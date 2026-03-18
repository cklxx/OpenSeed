"""Research session sharing — export/import for collaboration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from openseed.models.paper import Paper
from openseed.models.research import ResearchSession
from openseed.storage.library import PaperLibrary

_EXPORT_VERSION = 1


def export_session(
    session: ResearchSession, lib: PaperLibrary, include_papers: bool = True
) -> dict:
    """Export a research session as a shareable JSON bundle."""
    papers = []
    if include_papers:
        for pid in session.paper_ids:
            p = lib.get_paper(pid)
            if p:
                papers.append(p.model_dump(mode="json"))
    return {
        "version": _EXPORT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "session": session.model_dump(mode="json"),
        "papers": papers,
    }


def save_export(bundle: dict, dest: Path) -> Path:
    """Write export bundle to a JSON file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    return dest


def load_export(path: Path) -> dict:
    """Load an export bundle from a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def import_session(bundle: dict, lib: PaperLibrary) -> tuple[ResearchSession, int]:
    """Import a research session bundle into the library.

    Returns (session, papers_added_count).
    """
    session = ResearchSession(**bundle["session"])
    added = 0
    for paper_data in bundle.get("papers", []):
        paper = Paper.model_validate(paper_data)
        if lib.add_paper(paper):
            added += 1
    existing = lib.get_research_session(session.id)
    if not existing:
        lib.add_research_session(session)
    return session, added
