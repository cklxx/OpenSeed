"""OpenSeed MCP server — expose library and research tools via stdio."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from openseed.config import load_config
from openseed.storage.library import PaperLibrary

mcp = FastMCP("openseed")
_lib: PaperLibrary | None = None

_PAGE_SIZE = 20


def _get_library() -> PaperLibrary:
    global _lib  # noqa: PLW0603
    if _lib is None:
        _lib = PaperLibrary(load_config().library_dir)
    return _lib


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    """Return (text, was_truncated). Truncates at limit with clean break."""
    if len(text) <= limit:
        return text, False
    return text[:limit].rsplit(" ", 1)[0] + "…", True


def _paper_brief(p) -> dict:
    """Compact paper representation for list views."""
    tags = [t.name for t in p.tags] if p.tags else []
    return {"id": p.id, "title": p.title, "arxiv_id": p.arxiv_id, "status": p.status, "tags": tags}


def _paper_detail(p, section: str | None = None) -> dict:
    """Paper with abstract/summary preview. Use section='abstract'|'summary' for full text."""
    authors = [a.name for a in p.authors] if p.authors else []
    result: dict = {
        "id": p.id,
        "title": p.title,
        "arxiv_id": p.arxiv_id,
        "authors": authors,
        "status": p.status,
        "tags": [t.name for t in p.tags] if p.tags else [],
    }
    abstract = p.abstract or ""
    summary = p.summary or ""
    if section == "abstract":
        result["abstract"] = abstract
    elif section == "summary":
        result["summary"] = summary
    else:
        text, truncated = _truncate(abstract, 500)
        result["abstract"] = text
        if truncated:
            result["abstract_truncated"] = True
        text, truncated = _truncate(summary, 1000)
        result["summary"] = text
        if truncated:
            result["summary_truncated"] = True
    return result


def _paginated(items: list, offset: int, page_size: int) -> dict:
    """Wrap a list in pagination metadata."""
    page = items[offset : offset + page_size]
    has_more = offset + page_size < len(items)
    return {"items": page, "total": len(items), "offset": offset, "has_more": has_more}


@mcp.tool()
def search_papers(query: str, offset: int = 0) -> str:
    """Use when the user asks about papers on a topic, wants to find what's in their library,
    or references a paper by keyword. Returns matching papers from the local library (not web).
    Try this first before ask_research for simple lookups.
    Use offset to paginate if has_more is true."""
    papers = _get_library().search_papers(query)
    result = _paginated([_paper_brief(p) for p in papers], offset, _PAGE_SIZE)
    return json.dumps(result)


@mcp.tool()
def get_paper(paper_id: str, section: str | None = None) -> str:
    """Use when the user asks for details about a specific paper (abstract, summary, authors)
    and you already have the paper_id from search_papers or list_papers.
    Abstract and summary are previewed by default. If truncated, call again with
    section='abstract' or section='summary' to get the full text."""
    paper = _get_library().get_paper(paper_id)
    if paper is None:
        return json.dumps({"error": f"Paper {paper_id} not found"})
    return json.dumps(_paper_detail(paper, section))


@mcp.tool()
def list_papers(status: str | None = None, offset: int = 0) -> str:
    """Use when the user wants to see what papers are in their library, browse recent additions,
    or check library stats. Supports filtering by status: 'unread', 'read', 'archived'.
    Use offset to paginate if has_more is true."""
    papers = _get_library().list_papers()
    if status:
        papers = [p for p in papers if p.status == status]
    briefs = [_paper_brief(p) for p in papers]
    return json.dumps(_paginated(briefs, offset, _PAGE_SIZE))


@mcp.tool()
def get_graph(paper_id: str) -> str:
    """Use when the user asks how papers are connected, wants citation relationships,
    or asks 'what papers cite/reference this one'. Returns knowledge graph edges."""
    edges = _get_library().get_neighbors(paper_id)
    return json.dumps(edges)


@mcp.tool()
def ask_research(question: str) -> str:
    """Use ONLY when the user needs a synthesized answer that combines information across
    multiple papers — e.g. 'compare X and Y approaches' or 'what are the open problems in Z'.
    This is expensive (calls Claude API internally). For simple lookups, use search_papers."""
    from openseed.agent.assistant import ResearchAssistant

    lib = _get_library()
    assistant = ResearchAssistant(library=lib)
    return assistant.ask(question)


@mcp.tool()
def search_memories(query: str, offset: int = 0) -> str:
    """Use when the user references a prior research conversation or asks 'what did we
    discuss about X'. Searches saved conversation history from previous research sessions.
    Use offset to paginate if has_more is true."""
    from openseed.agent.memory import MemoryStore

    store = MemoryStore(_get_library())
    entries = store.search_memories(query, top_k=100)
    items = [
        {"session": e.session_id, "role": e.role, "content": e.content, "at": e.created_at}
        for e in entries
    ]
    return json.dumps(_paginated(items, offset, _PAGE_SIZE))


def run_mcp_server() -> None:
    """Start the MCP server with stdio transport."""
    mcp.run(transport="stdio")
