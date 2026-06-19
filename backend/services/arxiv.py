import re
from datetime import datetime

import feedparser
import httpx

ARXIV_API = "https://export.arxiv.org/api/query"
S2_REFERENCES_API = (
    "https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}/references"
)


def parse_arxiv_id_from_url(url: str) -> str | None:
    patterns = [
        r"arxiv\.org/abs/([\w./-]+)",
        r"arxiv\.org/pdf/([\w./-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            arxiv_id = match.group(1)
            if arxiv_id.endswith(".pdf"):
                arxiv_id = arxiv_id[:-4]
            return arxiv_id
    return None


async def fetch_metadata(arxiv_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ARXIV_API, params={"id_list": arxiv_id})
        response.raise_for_status()

    feed = feedparser.parse(response.text)
    if not feed.entries:
        raise ValueError(f"No metadata found for arXiv ID: {arxiv_id}")

    entry = feed.entries[0]
    title = entry.get("title", "").replace("\n", " ").strip()
    abstract = entry.get("summary", "").replace("\n", " ").strip()
    authors = [author.get("name", "") for author in entry.get("authors", [])]

    published = entry.get("published", "")
    year = datetime.fromisoformat(published.replace("Z", "+00:00")).year if published else None

    clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id

    return {
        "arxiv_id": clean_id,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "url": f"https://arxiv.org/abs/{clean_id}",
        "pdf_url": f"https://arxiv.org/pdf/{clean_id}.pdf",
    }


async def fetch_references(arxiv_id: str) -> list[str]:
    url = S2_REFERENCES_API.format(arxiv_id=arxiv_id)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"fields": "externalIds,title"})
            if response.status_code != 200:
                return []
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    arxiv_ids: list[str] = []
    for ref in data.get("data", []):
        external_ids = ref.get("externalIds") or {}
        arxiv_ref = external_ids.get("ArXiv")
        if arxiv_ref:
            arxiv_ids.append(str(arxiv_ref))

    return arxiv_ids
