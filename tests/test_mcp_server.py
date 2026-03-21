"""Tests for MCP server tool functions."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from openseed.models.paper import Author, Paper
from openseed.storage.library import PaperLibrary


@pytest.fixture
def lib(tmp_path):
    library = PaperLibrary(tmp_path / "library")
    p = Paper(
        title="Attention Is All You Need",
        authors=[Author(name="Vaswani")],
        abstract="Transformer architecture.",
        arxiv_id="1706.03762",
    )
    library.add_paper(p)
    return library


@pytest.fixture(autouse=True)
def patch_lib(lib):
    with patch("openseed.mcp.server._get_library", return_value=lib):
        yield


def test_search_papers_returns_json():
    from openseed.mcp.server import search_papers

    result = json.loads(search_papers("attention"))
    assert isinstance(result, list)
    assert any("Attention" in p["title"] for p in result)


def test_search_papers_empty():
    from openseed.mcp.server import search_papers

    result = json.loads(search_papers("nonexistent_xyz_query"))
    assert result == []


def test_get_paper_found(lib):
    from openseed.mcp.server import get_paper

    paper_id = lib.list_papers()[0].id
    result = json.loads(get_paper(paper_id))
    assert result["title"] == "Attention Is All You Need"


def test_get_paper_not_found():
    from openseed.mcp.server import get_paper

    result = json.loads(get_paper("nonexistent"))
    assert "error" in result


def test_list_papers_all():
    from openseed.mcp.server import list_papers

    result = json.loads(list_papers())
    assert len(result) == 1


def test_list_papers_filter_status():
    from openseed.mcp.server import list_papers

    result = json.loads(list_papers(status="unread"))
    assert len(result) == 1
    result = json.loads(list_papers(status="read"))
    assert len(result) == 0


def test_get_graph():
    from openseed.mcp.server import get_graph

    result = json.loads(get_graph("nonexistent"))
    assert isinstance(result, list)


def test_search_memories():
    from openseed.mcp.server import search_memories

    result = json.loads(search_memories("attention"))
    assert isinstance(result, list)


@patch("openseed.agent.assistant._ask")
def test_ask_research(mock_ask):
    mock_ask.return_value = "Transformers use self-attention."
    from openseed.mcp.server import ask_research

    result = ask_research("What are transformers?")
    assert "attention" in result.lower()
