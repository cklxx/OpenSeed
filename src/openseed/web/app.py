"""FastAPI web dashboard for OpenSeed."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from openseed.config import load_config
from openseed.storage.library import PaperLibrary
from openseed.storage.pool import LibraryPool

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_pool: LibraryPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = LibraryPool(load_config().library_dir)
    yield
    if _pool is not None:
        _pool.close()


app = FastAPI(title="OpenSeed", docs_url=None, redoc_url=None, lifespan=lifespan)
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@app.middleware("http")
async def _auth(request: Request, call_next):
    """Enforce API key auth when OPENSEED_API_KEY is set; open access otherwise."""
    api_key = os.environ.get("OPENSEED_API_KEY")
    if not api_key:
        return await call_next(request)
    auth = request.headers.get("Authorization", "")
    if auth == f"Bearer {api_key}":
        return await call_next(request)
    return JSONResponse({"error": "Invalid or missing API key"}, status_code=401)


def get_lib() -> Iterator[PaperLibrary]:
    """FastAPI dependency: borrow a PaperLibrary from the pool."""
    assert _pool is not None, "LibraryPool not initialized"
    with _pool.acquire() as lib:
        yield lib


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, lib: PaperLibrary = Depends(get_lib)):
    papers = lib.list_papers()
    stats = {
        "total": len(papers),
        "unread": sum(1 for p in papers if p.status == "unread"),
        "reading": sum(1 for p in papers if p.status == "reading"),
        "read": sum(1 for p in papers if p.status == "read"),
        "edges": lib.edge_count(),
        "clusters": len(lib.get_clusters()),
    }
    return templates.TemplateResponse(request, "index.html", {"stats": stats})


@app.get("/papers", response_class=HTMLResponse)
async def papers_list(
    request: Request,
    lib: PaperLibrary = Depends(get_lib),
    status: str | None = None,
    q: str | None = None,
):
    papers = lib.search_papers(q) if q else lib.list_papers()
    if status:
        papers = [p for p in papers if p.status == status]
    return templates.TemplateResponse(
        request, "papers.html", {"papers": papers, "status": status, "q": q or ""}
    )


@app.get("/papers/{paper_id}", response_class=HTMLResponse)
async def paper_detail(request: Request, paper_id: str, lib: PaperLibrary = Depends(get_lib)):
    paper = lib.get_paper(paper_id)
    if not paper:
        return HTMLResponse("<h1>Paper not found</h1>", status_code=404)
    neighbors = lib.get_neighbors(paper_id)
    neighbor_papers = []
    for n in neighbors:
        p = lib.get_paper(n["paper_id"])
        if p:
            neighbor_papers.append({"paper": p, "edge_type": n["edge_type"]})
    return templates.TemplateResponse(
        request, "paper_detail.html", {"paper": paper, "neighbors": neighbor_papers}
    )


@app.get("/graph", response_class=HTMLResponse)
async def graph_view(request: Request, lib: PaperLibrary = Depends(get_lib)):
    papers = lib.list_papers()
    edges = lib.list_all_edges()
    clusters = lib.get_clusters()
    paper_map = {p.id: p for p in papers}
    neighbor_counts = lib.get_neighbor_counts()
    nodes = [
        {"id": p.id, "title": p.title[:40], "connections": neighbor_counts[p.id]}
        for p in papers
        if p.id in neighbor_counts
    ]
    return templates.TemplateResponse(
        request,
        "graph.html",
        {"nodes": nodes, "edges": edges, "clusters": clusters, "paper_map": paper_map},
    )


@app.get("/digests", response_class=HTMLResponse)
async def digests_list(request: Request):
    config = load_config()
    digest_dir = Path(config.config_dir) / "digests"
    digests = []
    if digest_dir.exists():
        for f in sorted(digest_dir.glob("digest_*.md"), reverse=True):
            digests.append({"name": f.stem, "content": f.read_text(encoding="utf-8")})
    return templates.TemplateResponse(request, "digests.html", {"digests": digests})


@app.get("/sessions", response_class=HTMLResponse)
async def sessions_list(request: Request, lib: PaperLibrary = Depends(get_lib)):
    sessions = lib.list_research_sessions()
    return templates.TemplateResponse(request, "sessions.html", {"sessions": sessions})
