"""One-off demo data for graph UI testing."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from db.database import async_session, init_db
from db.models import Edge, Paper

DEMO_PAPERS = [
    {
        "arxiv_id": "1206.5538",
        "title": "Sequence to Sequence Learning with Neural Networks",
        "read": True,
        "gap_score": None,
        "is_frontier": False,
    },
    {
        "arxiv_id": "1310.4546",
        "title": "Distributed Representations of Words and Phrases",
        "read": False,
        "gap_score": 0.72,
        "is_frontier": False,
    },
    {
        "arxiv_id": "1508.07909",
        "title": "Neural Turing Machines",
        "read": False,
        "gap_score": None,
        "is_frontier": True,
    },
    {
        "arxiv_id": "1607.06450",
        "title": "Layer Normalization",
        "read": True,
        "gap_score": None,
        "is_frontier": False,
    },
    {
        "arxiv_id": "1809.02789",
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "read": False,
        "gap_score": 0.65,
        "is_frontier": True,
    },
    {
        "arxiv_id": "2005.14165",
        "title": "Language Models are Few-Shot Learners (GPT-3)",
        "read": False,
        "gap_score": None,
        "is_frontier": False,
    },
    {
        "arxiv_id": "2103.00020",
        "title": "Learning Transferable Visual Models (CLIP)",
        "read": False,
        "gap_score": 0.55,
        "is_frontier": False,
    },
]

DEMO_EDGES = [
    ("1706.03762", "1206.5538"),
    ("1706.03762", "1310.4546"),
    ("1706.03762", "1607.06450"),
    ("1409.0473", "1206.5538"),
    ("1409.0473", "1706.03762"),
    ("1809.02789", "1706.03762"),
    ("1809.02789", "1607.06450"),
    ("2005.14165", "1809.02789"),
    ("2005.14165", "1706.03762"),
    ("2103.00020", "2005.14165"),
    ("1508.07909", "1206.5538"),
    ("1108.6180", "1706.03762"),
]


async def main() -> None:
    await init_db()
    async with async_session() as db:
        id_by_arxiv: dict[str, int] = {}
        result = await db.execute(select(Paper))
        for paper in result.scalars():
            id_by_arxiv[paper.arxiv_id] = paper.id

        for item in DEMO_PAPERS:
            if item["arxiv_id"] in id_by_arxiv:
                paper = (
                    await db.execute(select(Paper).where(Paper.arxiv_id == item["arxiv_id"]))
                ).scalar_one()
                paper.read = item["read"]
                paper.gap_score = item["gap_score"]
                paper.is_frontier = item["is_frontier"]
                paper.crawled = True
                continue

            paper = Paper(
                arxiv_id=item["arxiv_id"],
                title=item["title"],
                authors=json.dumps(["Demo Author"]),
                year=2017,
                url=f"https://arxiv.org/abs/{item['arxiv_id']}",
                pdf_url=f"https://arxiv.org/pdf/{item['arxiv_id']}.pdf",
                read=item["read"],
                seed=False,
                crawled=True,
                crawl_depth=1,
                gap_score=item["gap_score"],
                is_frontier=item["is_frontier"],
            )
            db.add(paper)
            await db.flush()
            id_by_arxiv[item["arxiv_id"]] = paper.id

        edges_added = 0
        for source_arxiv, target_arxiv in DEMO_EDGES:
            source_id = id_by_arxiv.get(source_arxiv)
            target_id = id_by_arxiv.get(target_arxiv)
            if not source_id or not target_id:
                continue
            existing = (
                await db.execute(
                    select(Edge).where(
                        Edge.source_id == source_id,
                        Edge.target_id == target_id,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                continue
            db.add(Edge(source_id=source_id, target_id=target_id))
            edges_added += 1

        await db.commit()

        papers = (await db.execute(select(Paper))).scalars().all()
        edges = (await db.execute(select(Edge))).scalars().all()
        print(f"Demo seed complete: {len(papers)} papers, {len(edges)} edges (+{edges_added} new)")


if __name__ == "__main__":
    asyncio.run(main())
