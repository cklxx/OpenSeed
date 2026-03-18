"""Paper comparison — structured side-by-side analysis via Claude."""

from __future__ import annotations

from collections.abc import Callable

from openseed.agent.reader import _ask

_COMPARE_SYSTEM = (
    "You are a research paper comparison expert. Compare the two papers below "
    "and produce a structured markdown analysis with these sections:\n"
    "## Methodology Comparison\n"
    "## Shared Assumptions\n"
    "## Contradictory Findings\n"
    "## Complementary Strengths\n"
    "## Key Differences Summary (bullet list)\n"
    "Be specific — reference concrete details from each paper."
)


def compare_papers(
    text_a: str,
    text_b: str,
    title_a: str,
    title_b: str,
    model: str,
    on_step: Callable[[str], None] | None = None,
) -> str:
    """Generate a structured comparison of two papers."""
    prompt = f"## Paper A: {title_a}\n{text_a}\n\n---\n\n## Paper B: {title_b}\n{text_b}"
    return _ask(model, _COMPARE_SYSTEM, prompt, on_step=on_step)
