"""Paper discovery — Claude-powered search + Semantic Scholar enrichment."""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Callable
from datetime import date

from openseed.agent.reader import _ask

_log = logging.getLogger(__name__)
_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")


def _fetch_citations(arxiv_ids: list[str]) -> dict[str, int]:
    from openseed.services.scholar import fetch_citation_counts

    return fetch_citation_counts(arxiv_ids)


def _parse_ranked_lines(raw: str) -> list[dict]:
    raw = re.sub(r"```[a-z]*\n?", "", raw).strip().strip("```")
    papers = []
    skipped = 0
    for line in raw.strip().splitlines():
        parts = line.strip().split("|")
        if len(parts) < 3:
            skipped += 1
            continue
        arxiv_id = parts[0].strip()
        if not _ARXIV_ID_RE.match(arxiv_id):
            skipped += 1
            continue
        try:
            papers.append(
                {
                    "arxiv_id": arxiv_id,
                    "citations": int(
                        parts[1].strip().replace(",", "").replace("+", "").replace("~", "")
                    ),
                    "title": parts[2].strip(),
                    "authors": parts[3].strip() if len(parts) > 3 else "",
                    "relevance": parts[4].strip() if len(parts) > 4 else "",
                }
            )
        except (ValueError, IndexError):
            skipped += 1
    if not papers and raw.strip():
        _log.warning(
            "discover_papers: 0 valid lines parsed (skipped=%d). Head: %.200s", skipped, raw
        )
    return papers


def discover_papers(
    search_query: str,
    model: str,
    count: int = 10,
    since_year: int | None = None,
    on_step: Callable[[str], None] | None = None,
) -> list[dict]:
    """Phase 1: Claude web search -> parsed paper list with estimated citations."""
    recency = f" published in {since_year} or later" if since_year else ""
    scope = f"recent papers{recency}" if since_year else "highly-cited, high-impact papers"
    system = (
        "You are a research paper discovery assistant with web search access. "
        f"Find {count} {scope} about the given topic. "
        "Strategy: first identify core concepts and related terms, then search "
        "Semantic Scholar and Google Scholar for the most relevant papers in this area. "
        "Output ONLY pipe-separated lines — no markdown, no headers, no explanation:\n"
        "ARXIV_ID|ESTIMATED_CITATIONS|TITLE|FIRST_AUTHOR_ET_AL|ONE_LINE_RELEVANCE\n"
        "Example: 1706.03762|120000|Attention Is All You Need"
        "|Vaswani et al.|Transformer architecture\n"
        "Only include papers with valid ArXiv IDs. Sort descending by citation count."
    )
    raw = _ask(model, system, f"Find {count} papers about: {search_query}", on_step=on_step)
    return _parse_ranked_lines(raw)


def _freshness_score(arxiv_id: str, citations: int) -> tuple[int, float]:
    """Return (pub_year, score) where score = citations^0.6 * (1 + freshness)."""
    match = re.match(r"^(\d{2})(\d{2})\.", arxiv_id)
    if match:
        yy, mm = int(match.group(1)), int(match.group(2))
        year = 2000 + yy if yy <= 99 else yy
        pub = date(year, max(1, min(mm, 12)), 1)
    else:
        pub = date(2010, 1, 1)
    today = date.today()
    age_months = max((today.year - pub.year) * 12 + (today.month - pub.month), 1)
    freshness = math.exp(-age_months / 18)
    return pub.year, citations**0.6 * (1 + freshness)


def enrich_citations(papers: list[dict]) -> list[dict]:
    """Phase 2: Replace estimated citations with real counts; rank by freshness-weighted score."""
    real = _fetch_citations([p["arxiv_id"] for p in papers])
    for p in papers:
        if p["arxiv_id"] in real:
            p["citations"] = real[p["arxiv_id"]]
        p["year"], p["score"] = _freshness_score(p["arxiv_id"], p["citations"])
    return sorted(papers, key=lambda x: x["score"], reverse=True)


def search_papers_ranked(search_query: str, model: str, count: int = 10) -> list[dict]:
    """Full pipeline: discover via Claude + verify via Semantic Scholar."""
    return enrich_citations(discover_papers(search_query, model, count))


def search_papers_agent(
    search_query: str,
    model: str,
    count: int = 10,
    on_step: Callable[[str], None] | None = None,
) -> str:
    """Deep search using Claude web access — rich markdown output for pipeline command."""
    system = (
        "You are a research paper discovery assistant with web search access. "
        f"Find {count} high-value, highly-cited papers about the given topic. "
        "For each paper include: ArXiv ID, title, first 2 authors, year, "
        "citation count (from Semantic Scholar), and a one-sentence relevance note. "
        "Format as a markdown table: ArXiv ID | Title | Authors | Year | Citations | Relevance. "
        "Prioritize highly-cited papers. Use multiple searches to reach the target count. "
        "End with a ~150-word summary of key trends in this research area."
    )
    return _ask(model, system, f"Find {count} papers about: {search_query}", on_step=on_step)
