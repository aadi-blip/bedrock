import json
import re
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import CrawlJob, Edge, Paper
from services.arxiv import parse_arxiv_id_from_url
from services.crawler import crawl

router = APIRouter()


class SeedRequest(BaseModel):
    url: str
    depth: int = 2


class ReadUpdate(BaseModel):
    read: bool


def paper_to_dict(paper: Paper) -> dict:
    authors = []
    if paper.authors:
        try:
            authors = json.loads(paper.authors)
        except json.JSONDecodeError:
            authors = []

    return {
        "id": paper.id,
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": authors,
        "year": paper.year,
        "url": paper.url,
        "pdf_url": paper.pdf_url,
        "read": paper.read,
        "seed": paper.seed,
        "digest": paper.digest,
        "digest_generated_at": paper.digest_generated_at.isoformat() if paper.digest_generated_at else None,
        "crawled": paper.crawled,
        "crawl_depth": paper.crawl_depth,
        "gap_score": paper.gap_score,
        "is_frontier": paper.is_frontier,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
    }


def crawl_job_to_dict(job: CrawlJob) -> dict:
    return {
        "id": job.id,
        "arxiv_id": job.arxiv_id,
        "status": job.status,
        "depth": job.depth,
        "papers_found": job.papers_found,
        "edges_found": job.edges_found,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_msg": job.error_msg,
    }


@router.post("/seed")
async def seed_paper(
    body: SeedRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    arxiv_id = parse_arxiv_id_from_url(body.url)
    if not arxiv_id:
        raise HTTPException(status_code=400, detail="Invalid arXiv URL")

    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)

    result = await db.execute(select(Paper).where(Paper.arxiv_id == arxiv_id))
    paper = result.scalar_one_or_none()
    if paper is None:
        paper = Paper(
            arxiv_id=arxiv_id,
            url=f"https://arxiv.org/abs/{arxiv_id}",
            pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            seed=True,
        )
        db.add(paper)
    else:
        paper.seed = True

    job = CrawlJob(arxiv_id=arxiv_id, status="pending", depth=body.depth)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(crawl, arxiv_id, body.depth, job.id)

    return {"job_id": job.id, "arxiv_id": arxiv_id, "status": "pending"}


@router.get("/graph")
async def get_graph(db: AsyncSession = Depends(get_db)):
    papers_result = await db.execute(select(Paper))
    papers = papers_result.scalars().all()

    edges_result = await db.execute(select(Edge))
    edges = edges_result.scalars().all()

    nodes = [paper_to_dict(p) for p in papers]
    edge_list = [{"source": e.source_id, "target": e.target_id} for e in edges]

    read_count = sum(1 for p in papers if p.read)
    gap_nodes = [p.id for p in papers if p.gap_score is not None and p.gap_score > 0.5]

    return {
        "nodes": nodes,
        "edges": edge_list,
        "meta": {
            "total_papers": len(papers),
            "read_count": read_count,
            "gap_nodes": gap_nodes,
        },
    }


@router.get("/paper/{paper_id}")
async def get_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper_to_dict(paper)


@router.patch("/paper/{paper_id}/read")
async def update_paper_read(
    paper_id: int,
    body: ReadUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper.read = body.read
    await db.commit()
    await db.refresh(paper)
    return paper_to_dict(paper)


@router.get("/crawl/{job_id}")
async def get_crawl_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CrawlJob).where(CrawlJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    return crawl_job_to_dict(job)
