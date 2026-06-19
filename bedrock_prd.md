# Bedrock — Product Requirements Document

> **Tagline:** Drop a paper. See the universe of knowledge behind it. Find your frontier.

---

## 0. TL;DR

Bedrock is a personal research intelligence tool. You paste an arXiv URL, and it:
1. Crawls that paper's citation graph recursively (depth-configurable)
2. Stores every discovered paper in a local SQLite database
3. Renders an interactive D3 force-directed knowledge graph in the browser
4. Uses Claude to generate a one-paragraph digest for each paper
5. Runs a gap analysis — identifying which unread papers are *critical path* to understanding the ones you care about
6. Visually marks your **knowledge frontier**: the boundary between what you know and what you don't

No existing tool does personalised gap analysis grounded in citation topology. That's the moat.

---

## SETUP — Do This Before Opening Cursor

Follow these steps exactly, in order.

### Step 1 — Add your API key

Create `backend/.env` manually (Cursor can't do this):

```
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
DATABASE_URL=sqlite:///./db/bedrock.db
CORS_ORIGINS=http://localhost:3000
MAX_CRAWL_DEPTH=3
CRAWL_RATE_LIMIT_SECONDS=1.2
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 2 — Create `.cursorrules` at project root

Create a file called `.cursorrules` (no extension) at the root of the project with this content:

```
You are building Bedrock, an arXiv citation graph explorer.

Stack: FastAPI (Python 3.11) + Next.js 14 App Router + TypeScript + Tailwind CSS + D3.js + SQLite/SQLAlchemy (async).

Rules:
- Never rewrite files that weren't asked about
- Minimal diffs only — don't touch working code
- Async SQLAlchemy patterns throughout (aiosqlite)
- All frontend API calls go to http://localhost:8000
- Never add dependencies not already in requirements.txt / package.json
- DB file lives at backend/db/bedrock.db (gitignored)
- If something is unclear, ask before writing
- After each prompt, do not move on — wait for confirmation
```

### Step 3 — Open Cursor

```bash
cursor .
```

### Step 4 — Run the 6 prompts in order

Each prompt = **new Composer session** (`Cmd+I`). Never continue a previous Composer. After each prompt: verify it works, then commit before starting the next one.

---

## Cursor Prompts — Exact Sequence

---

### PROMPT 1 — Scaffold + Backend Core

**Files to @tag:** `bedrock_prd.md` (the only time you tag the full PRD)

**New Composer → paste this:**

```
Build a full-stack app called Bedrock — a personal arXiv citation graph explorer.

First, run these shell commands in the terminal:
- git init
- Create a .gitignore with: node_modules/, __pycache__/, .env, .env.local, backend/db/bedrock.db, .next/, *.pyc, dist/

PROJECT STRUCTURE to create:
bedrock/
├── backend/
│   ├── main.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── crawl.py
│   │   └── intel.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── arxiv.py
│   │   ├── crawler.py
│   │   ├── claude.py
│   │   └── graph_analysis.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── models.py
│   └── requirements.txt
└── frontend/
    ├── app/
    │   ├── page.tsx
    │   └── layout.tsx
    ├── components/
    │   ├── Graph.tsx
    │   ├── NodePanel.tsx
    │   ├── SeedInput.tsx
    │   ├── FilterBar.tsx
    │   └── Legend.tsx
    ├── hooks/
    │   ├── useGraph.ts
    │   └── usePaper.ts
    ├── lib/
    │   └── api.ts
    ├── types/
    │   └── index.ts
    └── package.json

BACKEND — implement fully:

1. db/models.py — SQLAlchemy async models:
   Table papers: id (PK), arxiv_id (TEXT UNIQUE NOT NULL), title (TEXT), abstract (TEXT), authors (TEXT — JSON array), year (INTEGER), url (TEXT), pdf_url (TEXT), read (BOOLEAN DEFAULT False), seed (BOOLEAN DEFAULT False), digest (TEXT nullable), digest_generated_at (DATETIME), crawled (BOOLEAN DEFAULT False), crawl_depth (INTEGER), gap_score (FLOAT nullable), is_frontier (BOOLEAN DEFAULT False), created_at (DATETIME DEFAULT now)
   Table edges: id (PK), source_id (FK papers.id), target_id (FK papers.id), created_at. UNIQUE on (source_id, target_id).
   Table crawl_jobs: id (PK), arxiv_id (TEXT), status (TEXT: pending/running/done/error), depth (INTEGER), papers_found (INTEGER DEFAULT 0), edges_found (INTEGER DEFAULT 0), created_at (DATETIME), finished_at (DATETIME nullable), error_msg (TEXT nullable)

2. db/database.py — async SQLite engine with aiosqlite. init_db() creates all tables. get_db() async session factory.

3. services/arxiv.py — two functions:
   fetch_metadata(arxiv_id: str) -> dict: GET https://export.arxiv.org/api/query?id_list={arxiv_id}, parse Atom XML with feedparser, return {arxiv_id, title, abstract, authors (list), year (int), url, pdf_url}
   fetch_references(arxiv_id: str) -> list[str]: GET https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}/references?fields=externalIds,title, extract arxiv_ids from externalIds where "ArXiv" key exists. Return list of arxiv_id strings. On HTTP error return [].

4. services/crawler.py — async BFS crawl:
   crawl(seed_arxiv_id, depth, job_id, db): BFS queue starting from seed. For each paper: fetch_metadata → upsert into papers → fetch_references → upsert edges → if depth>0 enqueue children not already in DB. Update crawl_jobs.papers_found and edges_found as you go. Rate limit: asyncio.sleep(1.2) between arXiv calls. On completion set job status=done and finished_at.

5. routes/graph.py:
   POST /seed: body {url: str, depth: int=2}. Parse arxiv_id from URL (handle both arxiv.org/abs/ and arxiv.org/pdf/ formats). Insert paper with seed=True if not exists. Create crawl_job with status=pending. Run crawl() via BackgroundTasks. Return {job_id, arxiv_id, status: "pending"}.
   GET /graph: Return {nodes: [all papers], edges: [{source: source_id, target: target_id}], meta: {total_papers, read_count, gap_nodes: [ids of papers where gap_score > 0.5]}}
   GET /paper/{id}: Return single paper row.
   PATCH /paper/{id}/read: body {read: bool}. Update papers.read. Return updated paper.
   GET /crawl/{job_id}: Return crawl_job row.

6. main.py: FastAPI app, CORS for http://localhost:3000, include all routers, call init_db() on startup.

7. requirements.txt: fastapi, uvicorn, sqlalchemy, aiosqlite, feedparser, httpx, anthropic, python-dotenv, pypdf

FRONTEND — scaffold only (placeholder content):
- types/index.ts: TypeScript types for Paper, Edge, GraphData, CrawlJob matching the DB schema exactly
- lib/api.ts: typed async fetch functions for every endpoint (seedPaper, getGraph, getPaper, toggleRead, getDigest, runGapAnalysis, getCrawlJob)
- app/page.tsx: placeholder with just a "Bedrock" heading in the center
- All component files: empty exports with a placeholder div

Do not skip any file. Create everything.
```

**After this prompt:** Run `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`. Check http://localhost:8000/docs — all routes should appear. Then commit:
```bash
git add . && git commit -m "prompt-1: scaffold + backend core"
```

---

### PROMPT 2 — D3 Graph Component

**Files to @tag:** `frontend/types/index.ts` `frontend/lib/api.ts`

**New Composer → paste this:**

```
Build the Graph component in frontend/components/Graph.tsx. Requirements:

- Use D3 v7 force simulation (install if not in package.json)
- Props: { onNodeSelect: (paper: Paper | null) => void, highlightIds?: number[] }
- Fetch graph data from getGraph() on mount. Poll every 4 seconds.
- Force config:
    forceLink distance=80 strength=0.5
    forceManyBody strength=-200
    forceCenter at width/2, height/2
    forceCollide radius=20

NODE VISUAL ENCODING (apply in this priority order):
- seed=true → radius 14, stroke white strokeWidth 3
- read=true → fill #6EE7B7 (green)
- is_frontier=true → fill #818CF8 (indigo) + pulsing ring (CSS animation: scale 1→1.4, opacity 1→0, 1.5s infinite)
- gap_score > 0.5 → fill #FCD34D (amber), radius 11
- default unread → fill #374151 (dark grey), radius 8
- selected node → white outer ring, strokeWidth 3

INTERACTIONS:
- Click node → call onNodeSelect(paper)
- Click canvas background → call onNodeSelect(null)
- Scroll → zoom (d3.zoom, scale 0.1–4)
- Drag canvas → pan
- Drag node → reposition (fix node on drag end)
- Double-click node → log "crawl deeper: {arxiv_id}" to console (wire up later)

EDGES: thin lines, stroke #4B5563, opacity 0.4, no arrows

Add edge labels only on hover (show target paper title, truncated to 40 chars).

The component must fill 100% of its parent container. Use a ResizeObserver to refit on container resize.

Export default Graph.
```

**After this prompt:** Run `cd frontend && npm install && npm run dev`. Check http://localhost:3000 — you should see the Bedrock heading. No graph yet (no data). Then commit:
```bash
git add . && git commit -m "prompt-2: D3 graph component"
```

---

### PROMPT 3 — SeedInput + NodePanel + Wire Up Page

**Files to @tag:** `frontend/types/index.ts` `frontend/lib/api.ts` `frontend/components/Graph.tsx` `frontend/app/page.tsx`

**New Composer → paste this:**

```
Build two components and wire everything into page.tsx.

COMPONENT 1: frontend/components/SeedInput.tsx
Props: { onCrawlComplete: () => void }
- Text input: placeholder "Paste arXiv URL (e.g. arxiv.org/abs/1108.6180)"
- Validate on blur: must match arxiv.org/abs/ or arxiv.org/pdf/ pattern. Show red border + "Invalid arXiv URL" if bad.
- Depth selector: three buttons "1" "2" "3" styled as pill toggles. Default: 2.
- "Crawl" button: calls seedPaper(url, depth). On success, start polling getCrawlJob(job_id) every 2s.
- While crawling: show progress bar (indeterminate) + text "Crawling... X papers, Y edges found"
- On job status=done: call onCrawlComplete(), reset UI
- On job status=error: show error message in red
- Disable Crawl button while a crawl is in progress

COMPONENT 2: frontend/components/NodePanel.tsx
Props: { paper: Paper | null, onClose: () => void, onReadToggle: (paper: Paper) => void }
- If paper is null: show empty state "Click a node to explore"
- Paper title as a link to paper.url (opens in new tab), large bold
- Authors (join with ", ") + year in muted text
- Abstract: show first 300 chars with "Show more" toggle
- Digest section:
  - If paper.digest exists: show it in a styled blockquote
  - If not: show "Generate digest" button. On click: call POST /digest/{id} (add this to lib/api.ts: fetch(`/paper/${id}/digest`, {method:'POST'})), show loading spinner, then display the returned digest
- "Mark as read" / "Mark as unread" toggle button. On click: call toggleRead(paper.id, !paper.read), call onReadToggle with updated paper.
- Close button (×) top right calling onClose

UPDATE frontend/app/page.tsx:
- Layout: full viewport, dark background (#0F172A)
- Top bar: "Bedrock" logo left, SeedInput center-right
- Main area: Graph fills remaining height, NodePanel as fixed right sidebar (width 380px) sliding in when a node is selected
- Wire onNodeSelect from Graph → NodePanel paper prop
- Wire onCrawlComplete → refetch graph data (pass a refresh trigger to Graph)
- Wire onReadToggle → update local graph node state immediately (optimistic update)
```

**After this prompt:** Test end-to-end — paste `https://arxiv.org/abs/1108.6180`, depth 1, crawl, see graph populate, click a node, see the panel. Then commit:
```bash
git add . && git commit -m "prompt-3: SeedInput + NodePanel + page wiring"
```

---

### PROMPT 4 — Claude Integration (Digests)

**Files to @tag:** `backend/services/arxiv.py` `backend/db/models.py` `backend/routes/intel.py`

**New Composer → paste this:**

```
Implement Claude digest generation in the backend.

1. backend/services/claude.py:
   Load ANTHROPIC_API_KEY from environment via python-dotenv.
   Implement async generate_digest(title: str, abstract: str) -> str:
   Call claude-sonnet-4-6 via the Anthropic Python SDK with:

   system: "You are a research assistant helping a physics/ML researcher quickly understand papers. Given a paper title and abstract, write a single dense paragraph (4-6 sentences) covering: (1) the core problem being solved, (2) the key insight or method, (3) the main result, (4) why it matters downstream. Be precise and technical. Assume the reader has a strong physics/math background. Do not pad. Do not start with 'This paper'."

   user: "Title: {title}\n\nAbstract: {abstract}"

   max_tokens: 300. Return the text content of the response.

2. backend/routes/intel.py:
   POST /paper/{id}/digest:
   - Fetch paper from DB by id. Return 404 if not found.
   - Call generate_digest(paper.title, paper.abstract)
   - Save result to papers.digest and papers.digest_generated_at = now()
   - Return updated paper object

   Also add to the crawler (services/crawler.py): after the seed paper metadata is fetched and saved, automatically call generate_digest for the seed paper only (not all crawled papers — too slow). Save the digest to DB.

3. Register the intel router in main.py if not already done.

Make sure ANTHROPIC_API_KEY is loaded from backend/.env using load_dotenv() at the top of claude.py.
```

**After this prompt:** Crawl a paper, click a node, click "Generate digest" — you should see Claude's summary appear. Then commit:
```bash
git add . && git commit -m "prompt-4: Claude digest generation"
```

---

### PROMPT 5 — Gap Analysis

**Files to @tag:** `backend/db/models.py` `backend/db/database.py` `backend/routes/intel.py` `backend/services/crawler.py`

**New Composer → paste this:**

```
Implement the gap analysis system.

1. backend/services/graph_analysis.py:
   Implement async compute_gap_analysis(db) -> dict:

   a) Load all papers and edges from DB
   b) Build adjacency: for each paper, track which papers cite it (in_edges) and which it cites (out_edges)
   c) Get set of read_ids (papers where read=True)
   d) For each UNREAD paper, compute:
      - in_degree_from_read: count of papers in read_ids that have an edge pointing TO this paper
      - out_degree_to_read: count of papers in read_ids that this paper has an edge TO
      - raw_score = (in_degree_from_read * 0.6) + (out_degree_to_read * 0.4)
   e) Normalise raw_score to 0-1 range across all unread papers → gap_score
   f) frontier_ids: unread papers where in_degree_from_read > 0 (directly cited by something you've read)
   g) top gap nodes: papers sorted by gap_score descending, top 10

   For the top gap nodes, make ONE Claude call:
   system: "You are analyzing a citation graph for a researcher. For each gap node listed, write exactly one sentence explaining why it is important given what the researcher has already read. Be specific — mention which read papers depend on it. Respond ONLY as a JSON array: [{\"arxiv_id\": \"...\", \"reason\": \"...\"}]"
   user: JSON with {read_papers: [{arxiv_id, title}], gap_nodes: [{arxiv_id, title, cited_by_read: [titles], cites_read: [titles]}]}

   Parse the JSON response. Return {gap_nodes: [{...paper, gap_score, reason}], frontier_ids: [int]}

2. backend/routes/intel.py — add:
   POST /gap-analysis:
   - Call compute_gap_analysis(db)
   - Update papers table: set gap_score and is_frontier for all affected papers
   - Return {gap_nodes: [...], frontier_count: int}

3. Update GET /graph in routes/graph.py:
   - Include gap_score and is_frontier fields on every node in the response
   - meta.gap_nodes should be list of ids where gap_score > 0.5
```

**After this prompt:** Mark a few papers as read, click "Run gap analysis" (wire a temp button in NodePanel or directly hit /gap-analysis in the browser), refresh graph — gap nodes should turn amber, frontier nodes indigo. Then commit:
```bash
git add . && git commit -m "prompt-5: gap analysis"
```

---

### PROMPT 6 — FilterBar + Legend + Final Polish

**Files to @tag:** `frontend/components/Graph.tsx` `frontend/app/page.tsx` `frontend/types/index.ts`

**New Composer → paste this:**

```
Add the final UI layer: FilterBar, Legend, and visual polish.

COMPONENT 1: frontend/components/FilterBar.tsx
Props: { onFilterChange: (filters: FilterState) => void, onRunGapAnalysis: () => void, stats: {total: number, read: number, gap: number, frontier: number} }
FilterState type: { search: string, showOnlyRead: boolean, showOnlyGap: boolean, showOnlyFrontier: boolean, yearMin: number, yearMax: number }

- Search input: filters nodes client-side by title or author substring match (case-insensitive)
- Three toggle pill buttons: "Read only" / "Gap nodes" / "Frontier" (mutually exclusive)
- Year range: two number inputs (min/max year), default 1990–2026
- "Run gap analysis" button: calls onRunGapAnalysis which calls POST /gap-analysis then refreshes graph
- Stats bar below: "Total: X | Read: Y | Gap: Z | Frontier: W" in muted small text

COMPONENT 2: frontend/components/Legend.tsx
- Four colored swatches with labels:
  ● #6EE7B7 Read
  ● #818CF8 Frontier (pulsing dot)
  ● #FCD34D Gap node
  ● #374151 Unread
- Small, fixed bottom-left of the graph canvas, semi-transparent dark background

UPDATE frontend/components/Graph.tsx:
- Accept new prop: filters: FilterState
- When filters active: dim non-matching nodes to opacity 0.15, keep matching nodes full opacity
- Filtered-out nodes still participate in force simulation but are visually faded
- Double-click node: instead of console.log, call POST /seed with depth=1 for that node's arxiv_id (crawl deeper from that node)

UPDATE frontend/app/page.tsx:
- Add FilterBar below the top bar
- Add Legend inside the graph canvas area (bottom-left)
- Wire onRunGapAnalysis: call POST /gap-analysis then trigger graph refresh
- Wire onFilterChange: pass filters down to Graph
- Add loading overlay on graph canvas during crawl (semi-transparent dark with spinner)
- Handle empty state: if graph has 0 nodes, show centered instruction "Paste an arXiv URL above to begin"

GENERAL POLISH:
- All buttons: hover states, cursor pointer, transition 150ms
- NodePanel: smooth slide-in animation (translate from right, 200ms)
- Graph canvas: background #0F172A (matches page), no border
- Top bar: border-bottom 1px #1E293B, height 56px
- Font: use Inter (add to layout.tsx via next/font)
- Add a favicon: simple dark square with white "B"
```

**After this prompt:** Full end-to-end test. Then commit:
```bash
git add . && git commit -m "prompt-6: FilterBar + Legend + polish"
```

---

## 1. Goals & Non-Goals

### Goals
- Ship a fully working local app in ~2 days using Cursor
- Genuinely useful for STAPLE / physics research workflow
- Visually impressive enough to demo to a recruiter or post online
- LLM-powered intelligence layer, not just a dumb scraper
- Persistent state across sessions (SQLite, not in-memory)

### Non-Goals
- Multi-user / auth (single-user local tool)
- Mobile responsiveness (desktop browser only)
- Real-time collaborative graph editing
- Full PDF ingestion for every paper (abstract-level is sufficient for v1)

---

## 2. User Stories

| # | As a user I want to… | So that… |
|---|---|---|
| U1 | Paste an arXiv URL and have the system crawl its references | I don't have to manually chase citations |
| U2 | See the full citation graph rendered as an interactive node graph | I can visually understand the landscape of a field |
| U3 | Mark papers as "read" | The system knows my knowledge state |
| U4 | See which unread papers are *critical path* (gap nodes) | I know exactly what to read next |
| U5 | Click any node and read a Claude-generated digest | I get the gist without opening the PDF |
| U6 | See my knowledge frontier highlighted | I have a clear picture of where my understanding ends |
| U7 | Filter/search the graph by author, year, keyword | I can navigate large graphs efficiently |
| U8 | Re-open the app and have my graph persisted | I don't lose progress between sessions |
| U9 | Double-click a node to crawl deeper from it | I can go deeper on specific branches |

---

## 3. Architecture

```
bedrock/
├── .cursorrules
├── bedrock_prd.md
├── backend/
│   ├── main.py
│   ├── .env                      ← you create this manually
│   ├── routes/
│   │   ├── graph.py              # GET /graph, POST /seed, PATCH /paper/:id/read, GET /crawl/:job_id, GET /paper/:id
│   │   └── intel.py              # POST /paper/:id/digest, POST /gap-analysis
│   ├── services/
│   │   ├── arxiv.py              # fetch_metadata, fetch_references
│   │   ├── crawler.py            # BFS crawl with rate limiting
│   │   ├── claude.py             # generate_digest, gap reason generation
│   │   └── graph_analysis.py    # compute_gap_analysis
│   ├── db/
│   │   ├── database.py           # async engine, init_db, get_db
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   └── bedrock.db            # gitignored
│   └── requirements.txt
└── frontend/
    ├── app/
    │   ├── page.tsx              # root layout + wiring
    │   └── layout.tsx
    ├── components/
    │   ├── Graph.tsx             # D3 force graph
    │   ├── NodePanel.tsx         # paper detail sidebar
    │   ├── SeedInput.tsx         # URL input + crawl progress
    │   ├── FilterBar.tsx         # search + filters + gap analysis button
    │   └── Legend.tsx            # node color key
    ├── hooks/
    │   ├── useGraph.ts
    │   └── usePaper.ts
    ├── lib/
    │   └── api.ts                # typed fetch wrappers
    ├── types/
    │   └── index.ts              # Paper, Edge, GraphData, CrawlJob, FilterState
    ├── .env.local                ← you create this manually
    └── package.json
```

---

## 4. Database Schema (SQLite)

### Table: `papers`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `arxiv_id` | TEXT UNIQUE NOT NULL | e.g. `1108.6180` |
| `title` | TEXT | Full paper title |
| `abstract` | TEXT | Full abstract |
| `authors` | TEXT | JSON array of author name strings |
| `year` | INTEGER | Publication year |
| `url` | TEXT | Full arXiv URL |
| `pdf_url` | TEXT | Direct PDF URL |
| `read` | BOOLEAN DEFAULT False | User has marked as read |
| `seed` | BOOLEAN DEFAULT False | This was a user-seeded paper |
| `digest` | TEXT nullable | Claude-generated one-para summary |
| `digest_generated_at` | DATETIME | Timestamp of last digest generation |
| `crawled` | BOOLEAN DEFAULT False | References have been extracted |
| `crawl_depth` | INTEGER | Depth at which this paper was discovered |
| `gap_score` | FLOAT nullable | Computed gap importance score (0–1) |
| `is_frontier` | BOOLEAN DEFAULT False | Directly cited by a read paper |
| `created_at` | DATETIME DEFAULT now | |

### Table: `edges`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `source_id` | INTEGER FK → papers.id | Paper that cites |
| `target_id` | INTEGER FK → papers.id | Paper being cited |
| `created_at` | DATETIME DEFAULT now | |

**Unique constraint:** `(source_id, target_id)`

### Table: `crawl_jobs`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `arxiv_id` | TEXT | Paper being crawled |
| `status` | TEXT | `pending` / `running` / `done` / `error` |
| `depth` | INTEGER | Depth requested |
| `papers_found` | INTEGER DEFAULT 0 | Live counter |
| `edges_found` | INTEGER DEFAULT 0 | Live counter |
| `created_at` | DATETIME | |
| `finished_at` | DATETIME nullable | |
| `error_msg` | TEXT nullable | |

---

## 5. API Contract

| Method | Path | Description |
|---|---|---|
| POST | `/seed` | Start a crawl from an arXiv URL |
| GET | `/graph` | Full graph (nodes + edges + meta) |
| GET | `/paper/{id}` | Single paper with full abstract |
| PATCH | `/paper/{id}/read` | Toggle read status |
| GET | `/crawl/{job_id}` | Poll crawl job status |
| POST | `/paper/{id}/digest` | Generate Claude digest for paper |
| POST | `/gap-analysis` | Run gap analysis across full graph |

---

## 6. arXiv Scraping Strategy

**Metadata:** arXiv Atom API
```
https://export.arxiv.org/api/query?id_list={arxiv_id}
```
Parse with `feedparser`. Returns title, authors, abstract, published date.

**References:** Semantic Scholar API (primary)
```
https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}/references?fields=externalIds,title
```
Filter results where `externalIds.ArXiv` exists. No auth required.

**Fallback:** If S2 returns empty, download PDF and regex-match arXiv IDs (`\d{4}\.\d{4,5}` and legacy `hep-ph/\d{7}` patterns) from the references section using pypdf.

**Rate limits:** 1.2s between arXiv calls. Exponential backoff on HTTP 429.

---

## 7. Intelligence Layer (Claude)

### 7.1 Paper Digest

**System:**
```
You are a research assistant helping a physics/ML researcher quickly understand papers. Given a paper title and abstract, write a single dense paragraph (4-6 sentences) covering: (1) the core problem being solved, (2) the key insight or method, (3) the main result, (4) why it matters downstream. Be precise and technical. Assume the reader has a strong physics/math background. Do not pad. Do not start with "This paper".
```

**User:** `Title: {title}\n\nAbstract: {abstract}`

**Model:** `claude-sonnet-4-6` | **max_tokens:** 300

---

### 7.2 Gap Analysis — Scoring (local computation)

For each unread paper:
```
in_degree_from_read  = # read papers that cite this paper
out_degree_to_read   = # papers this paper cites that are read
raw_score            = (in_degree_from_read * 0.6) + (out_degree_to_read * 0.4)
gap_score            = normalise(raw_score) to [0, 1] across all unread papers
```

Frontier nodes = unread papers where `in_degree_from_read > 0`

---

### 7.3 Gap Analysis — Claude Reasoning (one call)

**System:**
```
You are analyzing a citation graph for a researcher. For each gap node listed, write exactly one sentence explaining why it is important given what the researcher has already read. Be specific — mention which read papers depend on it. Respond ONLY as a JSON array: [{"arxiv_id": "...", "reason": "..."}]
```

**User:**
```json
{
  "read_papers": [{"arxiv_id": "...", "title": "..."}],
  "gap_nodes": [{"arxiv_id": "...", "title": "...", "cited_by_read": ["..."], "cites_read": ["..."]}]
}
```

---

## 8. Node Visual Encoding

| State | Fill | Radius | Extra |
|---|---|---|---|
| Seed | #6EE7B7 or user-read color | 14 | White double ring |
| Read | #6EE7B7 | 8 | — |
| Frontier (unread, adjacent to read) | #818CF8 | 8 | Pulsing ring animation |
| Gap node (gap_score > 0.5) | #FCD34D | 11 | — |
| Default unread | #374151 | 8 | — |
| Selected | Any | same | White outer ring |

---

## 9. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Semantic Scholar returns no references | Fall back to pypdf + arXiv ID regex |
| arXiv rate limit (HTTP 429) | Exponential backoff, min 3s between retries |
| Graph too large (500+ nodes) | Cap crawl at depth 2 by default; double-click crawl adds depth incrementally |
| Claude API latency | Generate digests lazily on demand only |
| SQLite write contention during BFS crawl | Single async writer, aiosqlite handles serialisation |
| D3 + React DOM conflict | Use `useRef` for SVG, let D3 own the DOM inside it, React only mounts/unmounts |

---

## 10. Future Ideas (post-v1)

- **Semantic clustering:** embed abstracts, cluster nodes by topic, color-code clusters
- **Personal notes:** attach your own annotations to any node, full-text searchable
- **Export:** graph as JSON / PNG / Obsidian markdown
- **"Explain the path":** Claude narrates the intellectual lineage from paper A to paper B
- **Bedrock × Knowledge OS:** ingest your own PDFs/notes, bridge them to the arXiv graph
- **Influential citation flag:** surface papers with high S2 citation counts

---

*Bedrock v1 | Spider | June 2026*
