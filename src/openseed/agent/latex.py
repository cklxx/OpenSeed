"""LaTeX related-work export — turn synthesis into a \\section{Related Work} draft."""

from __future__ import annotations

import re

from openseed.models.paper import Paper, paper_to_bibtex

_LATEX_SPECIAL = str.maketrans(
    {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\^{}",
    }
)


def _escape_latex(text: str) -> str:
    return text.translate(_LATEX_SPECIAL)


def _bibtex_key(paper: Paper) -> str:
    return (paper.arxiv_id or paper.id).replace(".", "").replace("/", "")


def _make_cite_map(papers: list[Paper]) -> dict[str, str]:
    """Build {escaped_title: cite_key} for inline citation replacement."""
    return {_escape_latex(paper.title).lower(): _bibtex_key(paper) for paper in papers}


def _insert_citations(text: str, cite_map: dict[str, str]) -> str:
    """Replace paper title mentions with \\cite{key} references."""
    result = text
    for title_lower, key in sorted(cite_map.items(), key=lambda x: -len(x[0])):
        pattern = re.compile(re.escape(title_lower), re.IGNORECASE)
        result = pattern.sub(f"\\\\cite{{{key}}}", result, count=1)
    return result


def export_related_work(synthesis: str, papers: list[Paper]) -> tuple[str, str]:
    """Convert synthesis + papers into LaTeX section + BibTeX entries.

    Returns (latex_content, bibtex_content).
    """
    cite_map = _make_cite_map(papers)
    body = _escape_latex(synthesis)
    body = _insert_citations(body, cite_map)

    latex = f"\\section{{Related Work}}\n\\label{{sec:related}}\n\n{body}\n"

    bibtex = "\n\n".join(paper_to_bibtex(p) for p in papers)
    return latex, bibtex
