"""Tests for paper comparison and LaTeX export."""

from openseed.agent.latex import _bibtex_key, _escape_latex, export_related_work
from openseed.models.paper import Author, Paper


class TestLatexEscape:
    def test_special_chars(self) -> None:
        assert _escape_latex("A & B") == r"A \& B"
        assert _escape_latex("50%") == r"50\%"
        assert _escape_latex("$x$") == r"\$x\$"
        assert _escape_latex("item_1") == r"item\_1"

    def test_no_escape_needed(self) -> None:
        assert _escape_latex("Hello World") == "Hello World"


class TestBibtexKey:
    def test_arxiv_id(self) -> None:
        p = Paper(title="Test", arxiv_id="1706.03762")
        assert _bibtex_key(p) == "170603762"

    def test_fallback_to_id(self) -> None:
        p = Paper(id="abc123", title="Test")
        assert _bibtex_key(p) == "abc123"


class TestExportRelatedWork:
    def test_basic_export(self) -> None:
        papers = [
            Paper(
                title="Attention Is All You Need",
                arxiv_id="1706.03762",
                authors=[Author(name="Vaswani")],
            ),
            Paper(
                title="BERT",
                arxiv_id="1810.04805",
                authors=[Author(name="Devlin")],
            ),
        ]
        synthesis = (
            "The Transformer architecture introduced in Attention Is All You Need "
            "has been foundational. BERT extended this with bidirectional pretraining."
        )
        latex, bibtex = export_related_work(synthesis, papers)
        assert "\\section{Related Work}" in latex
        assert "\\cite{170603762}" in latex
        assert "\\cite{181004805}" in latex
        assert "@article{170603762" in bibtex
        assert "@article{181004805" in bibtex
        assert "Vaswani" in bibtex

    def test_special_chars_in_synthesis(self) -> None:
        papers = [Paper(title="Test Paper", arxiv_id="2301.00001")]
        synthesis = "Results show 95% accuracy & F1 > $0.9$"
        latex, _ = export_related_work(synthesis, papers)
        assert r"\%" in latex
        assert r"\&" in latex

    def test_empty_papers(self) -> None:
        latex, bibtex = export_related_work("Some synthesis text.", [])
        assert "\\section{Related Work}" in latex
        assert bibtex == ""

    def test_bibtex_format(self) -> None:
        p = Paper(
            title="My Paper",
            arxiv_id="2301.00001",
            authors=[Author(name="Alice"), Author(name="Bob")],
        )
        _, bibtex = export_related_work("text", [p])
        assert "Alice and Bob" in bibtex
        assert "eprint" in bibtex


class TestCompare:
    def test_compare_produces_structured_output(self) -> None:
        from unittest.mock import patch

        with patch("openseed.agent.compare._ask") as mock_ask:
            mock_ask.return_value = (
                "## Methodology Comparison\nA uses X, B uses Y.\n"
                "## Key Differences Summary\n- Different approaches"
            )
            from openseed.agent.compare import compare_papers

            result = compare_papers("text a", "text b", "Paper A", "Paper B", "model")
            assert "Methodology Comparison" in result
            assert "Key Differences" in result
            mock_ask.assert_called_once()
