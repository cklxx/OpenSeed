"""Watch execution service — run saved watches and return results."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from openseed.models.paper import Paper
from openseed.models.watch import ArxivWatch
from openseed.services.arxiv import search_papers
from openseed.storage.library import PaperLibrary

_ARXIV_YEAR_RE = re.compile(r"^(\d{2})\d{2}\.")


def _arxiv_year(arxiv_id: str | None) -> int | None:
    m = _ARXIV_YEAR_RE.match(arxiv_id or "")
    return (2000 + int(m.group(1))) if m else None


def run_single_watch(lib: PaperLibrary, watch: ArxivWatch) -> list[Paper]:
    """Execute a single watch query and return matching papers."""
    papers = search_papers(watch.query, max_results=20)
    results = [
        p
        for p in papers
        if watch.since_year is None or (_arxiv_year(p.arxiv_id) or 0) >= watch.since_year
    ]
    watch.last_run = datetime.now(UTC)
    lib.update_watch(watch)
    return results


def run_all_watches(lib: PaperLibrary) -> dict[str, list[Paper]]:
    """Run all saved watches and return {watch_id: [papers]} mapping."""
    watches = lib.list_watches()
    results: dict[str, list[Paper]] = {}
    for w in watches:
        results[w.id] = run_single_watch(lib, w)
    return results
