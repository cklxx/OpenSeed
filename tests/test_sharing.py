"""Tests for research session sharing (export/import)."""

from pathlib import Path

import pytest

from openseed.models.paper import Author, Paper
from openseed.models.research import ResearchSession
from openseed.services.sharing import export_session, import_session, load_export, save_export
from openseed.storage.library import PaperLibrary


@pytest.fixture
def lib(tmp_path: Path) -> PaperLibrary:
    lib = PaperLibrary(tmp_path / "library")
    lib.add_paper(
        Paper(id="p1", title="Paper A", arxiv_id="2401.00001", authors=[Author(name="A")])
    )
    lib.add_paper(
        Paper(id="p2", title="Paper B", arxiv_id="2401.00002", authors=[Author(name="B")])
    )
    return lib


@pytest.fixture
def session() -> ResearchSession:
    return ResearchSession(id="sess1", topic="attention mechanisms", paper_ids=["p1", "p2"])


class TestExport:
    def test_export_includes_papers(self, lib: PaperLibrary, session: ResearchSession) -> None:
        lib.add_research_session(session)
        bundle = export_session(session, lib)
        assert bundle["version"] == 1
        assert bundle["session"]["topic"] == "attention mechanisms"
        assert len(bundle["papers"]) == 2

    def test_export_without_papers(self, lib: PaperLibrary, session: ResearchSession) -> None:
        lib.add_research_session(session)
        bundle = export_session(session, lib, include_papers=False)
        assert len(bundle["papers"]) == 0

    def test_save_and_load(
        self, tmp_path: Path, lib: PaperLibrary, session: ResearchSession
    ) -> None:
        lib.add_research_session(session)
        bundle = export_session(session, lib)
        path = save_export(bundle, tmp_path / "export.json")
        assert path.exists()
        loaded = load_export(path)
        assert loaded["session"]["topic"] == "attention mechanisms"
        assert len(loaded["papers"]) == 2


class TestImport:
    def test_import_into_empty_library(self, tmp_path: Path, session: ResearchSession) -> None:
        source_lib = PaperLibrary(tmp_path / "source")
        source_lib.add_paper(
            Paper(id="p1", title="Paper A", arxiv_id="2401.00001", authors=[Author(name="A")])
        )
        source_lib.add_research_session(session)
        bundle = export_session(session, source_lib)
        dest_lib = PaperLibrary(tmp_path / "dest")
        imported_session, added = import_session(bundle, dest_lib)
        assert imported_session.topic == "attention mechanisms"
        assert added == 1
        assert len(dest_lib.list_papers()) == 1
        assert dest_lib.get_research_session("sess1") is not None

    def test_import_skips_existing_papers(
        self, lib: PaperLibrary, session: ResearchSession
    ) -> None:
        lib.add_research_session(session)
        bundle = export_session(session, lib)
        _, added = import_session(bundle, lib)
        assert added == 0

    def test_import_skips_existing_session(
        self, lib: PaperLibrary, session: ResearchSession
    ) -> None:
        lib.add_research_session(session)
        bundle = export_session(session, lib)
        imported, _ = import_session(bundle, lib)
        assert imported.id == "sess1"
        assert len(lib.list_research_sessions()) == 1
