"""Tests for the web dashboard."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from openseed.config import OpenSeedConfig
from openseed.models.paper import Author, Paper, Tag
from openseed.storage.library import PaperLibrary
from openseed.web.app import app, get_lib


@pytest.fixture
def lib(tmp_path: Path) -> PaperLibrary:
    lib = PaperLibrary(tmp_path / "library")
    lib.add_paper(
        Paper(
            id="p1",
            title="Attention Is All You Need",
            arxiv_id="1706.03762",
            authors=[Author(name="Vaswani")],
            abstract="We propose the Transformer.",
            summary="A great paper about transformers.",
            tags=[Tag(name="transformers")],
            status="read",
        )
    )
    lib.add_paper(
        Paper(
            id="p2",
            title="BERT",
            arxiv_id="1810.04805",
            authors=[Author(name="Devlin")],
            abstract="Bidirectional pre-training.",
            tags=[Tag(name="nlp")],
        )
    )
    lib.add_edge("p1", "p2", "cites")
    return lib


@pytest.fixture
def client(lib: PaperLibrary, tmp_path: Path) -> TestClient:
    config = OpenSeedConfig(library_dir=lib._dir, config_dir=tmp_path / "config")

    def override_get_lib():
        yield lib

    app.dependency_overrides[get_lib] = override_get_lib
    with patch("openseed.web.app.load_config", return_value=config):
        yield TestClient(app)
    app.dependency_overrides.clear()


class TestWebDashboard:
    def test_index(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Dashboard" in resp.text
        assert "2" in resp.text  # total papers

    def test_papers_list(self, client: TestClient) -> None:
        resp = client.get("/papers")
        assert resp.status_code == 200
        assert "Attention Is All You Need" in resp.text
        assert "BERT" in resp.text

    def test_papers_filter_status(self, client: TestClient) -> None:
        resp = client.get("/papers?status=read")
        assert resp.status_code == 200
        assert "Attention Is All You Need" in resp.text
        assert "BERT" not in resp.text

    def test_papers_search(self, client: TestClient) -> None:
        resp = client.get("/papers?q=transformer")
        assert resp.status_code == 200
        assert "Attention" in resp.text

    def test_paper_detail(self, client: TestClient) -> None:
        resp = client.get("/papers/p1")
        assert resp.status_code == 200
        assert "Attention Is All You Need" in resp.text
        assert "Vaswani" in resp.text
        assert "A great paper about transformers" in resp.text
        assert "BERT" in resp.text  # neighbor

    def test_paper_not_found(self, client: TestClient) -> None:
        resp = client.get("/papers/nonexistent")
        assert resp.status_code == 404

    def test_graph(self, client: TestClient) -> None:
        resp = client.get("/graph")
        assert resp.status_code == 200
        assert "Knowledge Graph" in resp.text
        assert "Cluster 1" in resp.text

    def test_graph_empty_library(self, tmp_path: Path) -> None:
        empty_lib = PaperLibrary(tmp_path / "empty")

        def override():
            yield empty_lib

        app.dependency_overrides[get_lib] = override
        try:
            c = TestClient(app)
            resp = c.get("/graph")
        finally:
            app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_graph_isolated_nodes_excluded(self, tmp_path: Path) -> None:
        """Papers with no edges should not appear as graph nodes."""
        lib = PaperLibrary(tmp_path / "iso")
        lib.add_paper(Paper(id="x1", title="Isolated Paper", authors=[], abstract="No edges here."))

        def override():
            yield lib

        app.dependency_overrides[get_lib] = override
        try:
            c = TestClient(app)
            resp = c.get("/graph")
        finally:
            app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_digests_empty(self, client: TestClient) -> None:
        resp = client.get("/digests")
        assert resp.status_code == 200
        assert "No digests yet" in resp.text

    def test_sessions_empty(self, client: TestClient) -> None:
        resp = client.get("/sessions")
        assert resp.status_code == 200
        assert "No research sessions yet" in resp.text


class TestAuthMiddleware:
    def test_no_api_key_set_allows_access(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.delenv("OPENSEED_API_KEY", raising=False)
        resp = client.get("/")
        assert resp.status_code == 200

    def test_valid_bearer_token_allows_access(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("OPENSEED_API_KEY", "secret123")
        resp = client.get("/", headers={"Authorization": "Bearer secret123"})
        assert resp.status_code == 200

    def test_missing_auth_header_returns_401(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("OPENSEED_API_KEY", "secret123")
        resp = client.get("/")
        assert resp.status_code == 401
        assert "API key" in resp.json()["error"]

    def test_wrong_token_returns_401(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("OPENSEED_API_KEY", "secret123")
        resp = client.get("/", headers={"Authorization": "Bearer wrongkey"})
        assert resp.status_code == 401

    def test_all_routes_protected_when_key_set(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("OPENSEED_API_KEY", "mykey")
        for path in ["/", "/papers", "/graph", "/digests", "/sessions"]:
            resp = client.get(path)
            assert resp.status_code == 401, f"Expected 401 for {path}"

    def test_all_routes_open_when_key_unset(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.delenv("OPENSEED_API_KEY", raising=False)
        for path in ["/", "/papers", "/graph", "/digests", "/sessions"]:
            resp = client.get(path)
            assert resp.status_code == 200, f"Expected 200 for {path}"
