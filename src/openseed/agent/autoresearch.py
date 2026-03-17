"""AutoResearcher — autonomous multi-round paper discovery and analysis."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from openseed.agent.reader import (
    PaperReader,
    _ask,
    auto_tag_paper,
    discover_papers,
    enrich_citations,
    synthesize_papers,
)
from openseed.models.paper import Paper, Tag
from openseed.models.research import ResearchSession
from openseed.services.arxiv import fetch_paper_metadata
from openseed.storage.library import PaperLibrary


class AutoResearcher:
    """Orchestrates multi-round discovery, analysis, synthesis, and reporting."""

    def __init__(self, model: str, lib: PaperLibrary) -> None:
        self._model = model
        self._lib = lib

    def run(
        self,
        topic: str,
        count: int = 15,
        depth: int = 2,
        on_step: Callable[[str], None] | None = None,
    ) -> ResearchSession:
        session = ResearchSession(topic=topic)
        variants = self._query_variants(topic, depth)
        session.query_variants = variants
        raw = self._multi_discover(variants, count)
        papers = self._batch_analyze(raw, on_step)
        session.paper_ids = [p.id for p in papers]
        session.synthesis = self._synthesize(papers, on_step)
        session.report = self._generate_report(session, papers, on_step)
        return session

    def _query_variants(self, topic: str, depth: int) -> list[str]:
        system = (
            "You are a research search strategist. Generate diverse search query variants "
            "to find papers about this topic from different angles. "
            "Return one query per line, no numbering, no extra text."
        )
        raw = _ask(self._model, system, f"Generate {depth} queries for: {topic}")
        lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
        return lines[:depth] or [topic]

    def _multi_discover(self, variants: list[str], total_count: int) -> list[dict]:
        per_query = max(total_count // max(len(variants), 1), 5)
        seen: set[str] = set()
        all_papers: list[dict] = []
        for variant in variants:
            for p in enrich_citations(discover_papers(variant, self._model, per_query)):
                if p["arxiv_id"] not in seen:
                    seen.add(p["arxiv_id"])
                    all_papers.append(p)
        return sorted(all_papers, key=lambda x: x.get("score", 0), reverse=True)[:total_count]

    def _batch_analyze(
        self, raw_papers: list[dict], on_step: Callable[[str], None] | None
    ) -> list[Paper]:
        result: list[Paper] = []
        for rd in raw_papers:
            paper = self._analyze_one(rd, on_step)
            if paper:
                result.append(paper)
        return result

    def _analyze_one(self, rd: dict, on_step: Callable[[str], None] | None) -> Paper | None:
        try:
            paper = asyncio.run(fetch_paper_metadata(rd["arxiv_id"]))
        except Exception:
            return None
        text = paper.abstract or paper.title
        if on_step:
            on_step(f"Summarizing: {paper.title[:40]}…")
        paper.summary = PaperReader(model=self._model).summarize_paper(text, on_step=on_step)
        paper.tags = [Tag(name=t) for t in auto_tag_paper(text, self._model)]
        self._lib.add_paper(paper)
        self._lib.save_summary(paper)
        return paper

    def _synthesize(self, papers: list[Paper], on_step: Callable[[str], None] | None) -> str:
        if not papers:
            return ""
        if on_step:
            on_step("Synthesizing across papers…")
        texts = [f"Title: {p.title}\n\n{p.summary or p.abstract or p.title}" for p in papers]
        return synthesize_papers(texts, self._model)

    def _build_report_prompt(self, session: ResearchSession, papers: list[Paper]) -> str:
        paper_list = "\n".join(
            f"- {p.title} ({p.arxiv_id}): {(p.summary or p.abstract or '')[:200]}" for p in papers
        )
        return (
            f"Research topic: {session.topic}\n\n"
            f"Papers analyzed:\n{paper_list}\n\n"
            f"Synthesis:\n{session.synthesis}"
        )

    def _generate_report(
        self,
        session: ResearchSession,
        papers: list[Paper],
        on_step: Callable[[str], None] | None,
    ) -> str:
        if not papers:
            return ""
        if on_step:
            on_step("Generating research report…")
        system = (
            "You are a research analyst. Generate a comprehensive research report in markdown. "
            "Include: ## Executive Summary, ## Research Landscape, ## Top Papers (table), "
            "## Key Themes, ## Research Gaps, ## Recommended Reading Order."
        )
        prompt = self._build_report_prompt(session, papers)
        return _ask(self._model, system, prompt, on_step=on_step)
