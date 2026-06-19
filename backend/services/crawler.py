import asyncio
import json
from collections import deque
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import async_session
from db.models import CrawlJob, Edge, Paper
from services.arxiv import fetch_metadata, fetch_references

RATE_LIMIT_SECONDS = 1.2


async def _get_paper_by_arxiv_id(db: AsyncSession, arxiv_id: str) -> Paper | None:
    result = await db.execute(select(Paper).where(Paper.arxiv_id == arxiv_id))
    return result.scalar_one_or_none()


async def _upsert_paper(
    db: AsyncSession,
    metadata: dict,
    *,
    seed: bool = False,
    crawl_depth: int,
) -> Paper:
    paper = await _get_paper_by_arxiv_id(db, metadata["arxiv_id"])
    authors_json = json.dumps(metadata.get("authors", []))

    if paper is None:
        paper = Paper(
            arxiv_id=metadata["arxiv_id"],
            title=metadata.get("title"),
            abstract=metadata.get("abstract"),
            authors=authors_json,
            year=metadata.get("year"),
            url=metadata.get("url"),
            pdf_url=metadata.get("pdf_url"),
            seed=seed,
            crawled=True,
            crawl_depth=crawl_depth,
        )
        db.add(paper)
    else:
        paper.title = metadata.get("title")
        paper.abstract = metadata.get("abstract")
        paper.authors = authors_json
        paper.year = metadata.get("year")
        paper.url = metadata.get("url")
        paper.pdf_url = metadata.get("pdf_url")
        paper.crawled = True
        paper.crawl_depth = crawl_depth
        if seed:
            paper.seed = True

    await db.flush()
    return paper


async def _upsert_edge(db: AsyncSession, source_id: int, target_id: int) -> bool:
    result = await db.execute(
        select(Edge).where(Edge.source_id == source_id, Edge.target_id == target_id)
    )
    if result.scalar_one_or_none() is not None:
        return False

    db.add(Edge(source_id=source_id, target_id=target_id))
    await db.flush()
    return True


async def _ensure_placeholder_paper(db: AsyncSession, arxiv_id: str, crawl_depth: int) -> Paper:
    paper = await _get_paper_by_arxiv_id(db, arxiv_id)
    if paper is None:
        paper = Paper(
            arxiv_id=arxiv_id,
            url=f"https://arxiv.org/abs/{arxiv_id}",
            pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            crawl_depth=crawl_depth,
        )
        db.add(paper)
        await db.flush()
    return paper


async def crawl(seed_arxiv_id: str, depth: int, job_id: int, db: AsyncSession | None = None) -> None:
    async def _run(session: AsyncSession) -> None:
        job_result = await session.execute(select(CrawlJob).where(CrawlJob.id == job_id))
        job = job_result.scalar_one()
        job.status = "running"
        await session.commit()

        queue: deque[tuple[str, int, bool]] = deque([(seed_arxiv_id, 0, True)])
        visited: set[str] = set()

        try:
            while queue:
                arxiv_id, current_depth, is_seed = queue.popleft()
                if arxiv_id in visited:
                    continue
                visited.add(arxiv_id)

                await asyncio.sleep(RATE_LIMIT_SECONDS)
                metadata = await fetch_metadata(arxiv_id)
                paper = await _upsert_paper(
                    session,
                    metadata,
                    seed=is_seed,
                    crawl_depth=current_depth,
                )
                await session.commit()

                job.papers_found = (job.papers_found or 0) + 1
                await session.commit()

                ref_ids = await fetch_references(arxiv_id)
                new_edges = 0

                for ref_id in ref_ids:
                    target = await _ensure_placeholder_paper(session, ref_id, current_depth + 1)
                    if await _upsert_edge(session, paper.id, target.id):
                        new_edges += 1

                job.edges_found = (job.edges_found or 0) + new_edges
                await session.commit()

                if current_depth < depth:
                    for ref_id in ref_ids:
                        existing = await _get_paper_by_arxiv_id(session, ref_id)
                        if existing is None or not existing.crawled:
                            queue.append((ref_id, current_depth + 1, False))

            job.status = "done"
            job.finished_at = datetime.utcnow()
            await session.commit()
        except Exception as exc:
            job.status = "error"
            job.error_msg = str(exc)
            job.finished_at = datetime.utcnow()
            await session.commit()
            raise

    if db is not None:
        await _run(db)
    else:
        async with async_session() as session:
            await _run(session)
