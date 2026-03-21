"""OpenSeed MCP server — expose library and research tools via stdio."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from openseed.config import load_config
from openseed.storage.library import PaperLibrary

mcp = FastMCP("openseed")
_lib: PaperLibrary | None = None


def _get_library() -> PaperLibrary:
    global _lib  # noqa: PLW0603
    if _lib is None:
        _lib = PaperLibrary(load_config().library_dir)
    return _lib


@mcp.tool()
def search_papers(query: str) -> str:
    """Full-text search across your paper library."""
    papers = _get_library().search_papers(query)
    return json.dumps([{"id": p.id, "title": p.title, "arxiv_id": p.arxiv_id} for p in papers])


@mcp.tool()
def get_paper(paper_id: str) -> str:
    """Get details for a specific paper by ID."""
    paper = _get_library().get_paper(paper_id)
    if paper is None:
        return json.dumps({"error": f"Paper {paper_id} not found"})
    return paper.model_dump_json()


@mcp.tool()
def list_papers(status: str | None = None) -> str:
    """List papers in the library, optionally filtered by status."""
    papers = _get_library().list_papers()
    if status:
        papers = [p for p in papers if p.status == status]
    return json.dumps([{"id": p.id, "title": p.title, "status": p.status} for p in papers])


@mcp.tool()
def get_graph(paper_id: str) -> str:
    """Get knowledge graph edges for a paper."""
    edges = _get_library().get_neighbors(paper_id)
    return json.dumps(edges)


@mcp.tool()
def ask_research(question: str) -> str:
    """Ask a context-aware research question grounded in your library."""
    from openseed.agent.assistant import ResearchAssistant

    lib = _get_library()
    assistant = ResearchAssistant(library=lib)
    return assistant.ask(question)


@mcp.tool()
def search_memories(query: str) -> str:
    """Search research conversation memory."""
    from openseed.agent.memory import MemoryStore

    store = MemoryStore(_get_library())
    entries = store.search_memories(query)
    return json.dumps(
        [
            {"session": e.session_id, "role": e.role, "content": e.content, "at": e.created_at}
            for e in entries
        ]
    )


def run_mcp_server() -> None:
    """Start the MCP server with stdio transport."""
    mcp.run(transport="stdio")
