"""PDF text extraction and Markdown conversion."""

from __future__ import annotations

import re
from pathlib import Path


def extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF file using pymupdf for better quality."""
    import fitz  # pymupdf

    with fitz.open(pdf_path) as doc:
        return "\n\n".join(page.get_text("text") for page in doc)


def extract_text_pages(pdf_path: str) -> list[dict[str, object]]:
    """Extract text page-by-page with page numbers."""
    import fitz  # pymupdf

    with fitz.open(pdf_path) as doc:
        return [{"page": i + 1, "text": page.get_text("text") or ""} for i, page in enumerate(doc)]


def _extract_page_blocks(page) -> list[dict]:
    """Return text blocks with font size info from a single page."""
    result = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s["text"] for s in spans).strip()
            if text:
                result.append(
                    {"text": text, "size": max(s["size"] for s in spans), "bbox": block["bbox"]}
                )
    return result


def _extract_all_blocks(doc) -> list[dict]:
    """Return text blocks with font size info from all pages."""
    blocks = []
    for page_num, page in enumerate(doc):
        for b in _extract_page_blocks(page):
            blocks.append({**b, "page": page_num + 1})
    return blocks


def _is_page_number(text: str) -> bool:
    """Return True if this line looks like a page number or running header/footer."""
    stripped = text.strip()
    if re.fullmatch(r"\d+", stripped):
        return True
    if re.fullmatch(r"[-–—]?\s*\d+\s*[-–—]?", stripped):
        return True
    return False


def _compute_font_stats(blocks: list[dict]) -> tuple[float, int, float]:
    """Return (median_size, title_idx, title_size) for font-based classification."""
    sizes = sorted(b["size"] for b in blocks)
    median_size = sizes[len(sizes) // 2]
    title_threshold = median_size * 1.40
    title_idx = next(
        (i for i, b in enumerate(blocks) if b["page"] == 1 and b["size"] >= title_threshold), 0
    )
    return median_size, title_idx, blocks[title_idx]["size"]


def _classify_block(block: dict, median_size: float) -> str:
    """Classify a block as 'skip', 'heading', or 'body'."""
    text, size = block["text"], block["size"]
    if _is_page_number(text) or re.match(r"^arXiv:\d{4}\.\d+", text):
        return "skip"
    heading_threshold = max(median_size * 1.20, median_size + 1.5)
    is_large = size >= heading_threshold
    is_caps = text.isupper() and len(text) <= 60
    is_numbered = bool(re.match(r"^\d+(\.\d+)*\.?\s+[A-Z]", text) and len(text) <= 80)
    return "heading" if (is_large or is_caps or is_numbered) else "body"


def _format_block(block: dict, classification: str) -> str:
    """Convert a classified block to its markdown representation."""
    text = block["text"]
    if classification == "heading":
        return f"\n## {text}\n"
    return text


def _flush_abstract(abstract_lines: list[str]) -> str:
    """Format collected abstract lines as a markdown abstract block."""
    return f"\n**Abstract:** {' '.join(abstract_lines).strip()}\n"


def _handle_abstract_keyword(text: str, state: dict) -> None:
    """Begin abstract collection, capturing any inline content."""
    state["in_abstract"] = True
    after = re.sub(r"^abstract\s*[:.]?\s*", "", text, flags=re.IGNORECASE).strip()
    if after:
        state["abstract_lines"].append(after)


def _handle_heading(block: dict, md_lines: list[str], state: dict) -> None:
    """Flush any pending abstract and append a heading line."""
    if state["in_abstract"]:
        md_lines.append(_flush_abstract(state["abstract_lines"]))
        state["abstract_lines"] = []
        state["in_abstract"] = False
    md_lines.append(_format_block(block, "heading"))


def _handle_body(text: str, md_lines: list[str], state: dict) -> None:
    """Append body text, or collect it into abstract if currently in abstract."""
    if state["in_abstract"]:
        state["abstract_lines"].append(text)
    else:
        if state["prev_text"] and state["prev_text"].endswith((".", ":")):
            md_lines.append("")
        md_lines.append(text)


def _process_block(
    block: dict, title_size: float, median_size: float, md_lines: list[str], state: dict
) -> None:
    """Route a single block to the appropriate handler."""
    text, size = block["text"], block["size"]
    classification = _classify_block(block, median_size)
    if classification == "skip":
        return
    if not state["title_written"] and size >= title_size * 0.95:
        md_lines.append(f"# {text}")
        state["title_written"] = True
    elif re.match(r"^abstract\b", text, re.IGNORECASE):
        _handle_abstract_keyword(text, state)
    elif classification == "heading":
        _handle_heading(block, md_lines, state)
    else:
        _handle_body(text, md_lines, state)
    state["prev_text"] = text


def _build_md_lines(blocks: list[dict], title_size: float, median_size: float) -> list[str]:
    """Process all blocks and return the list of markdown lines."""
    md_lines: list[str] = []
    state = {"title_written": False, "in_abstract": False, "abstract_lines": [], "prev_text": ""}
    for block in blocks:
        _process_block(block, title_size, median_size, md_lines, state)
    if state["in_abstract"] and state["abstract_lines"]:
        md_lines.append(_flush_abstract(state["abstract_lines"]))
    return md_lines


def pdf_to_markdown(pdf_path: str) -> str:
    """Convert a PDF to structured Markdown.

    Produces:
    - Title as ``# Title``
    - Section headings as ``## Section``
    - Abstract wrapped as ``**Abstract:** ...``
    - Paragraph breaks (double newlines)
    - Stripped page numbers and running headers/footers

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Clean Markdown string.
    """
    import fitz  # pymupdf

    with fitz.open(pdf_path) as doc:
        blocks = _extract_all_blocks(doc)
    if not blocks:
        return ""
    median_size, title_idx, title_size = _compute_font_stats(blocks)
    return "\n".join(_build_md_lines(blocks[title_idx:], title_size, median_size))


def save_markdown(pdf_path: str, md_content: str) -> str:
    """Save Markdown content alongside the PDF (replaces .pdf extension with .md).

    Args:
        pdf_path: Path to the source PDF file.
        md_content: Markdown string to save.

    Returns:
        Path to the saved .md file.
    """
    md_path = Path(pdf_path).with_suffix(".md")
    md_path.write_text(md_content, encoding="utf-8")
    return str(md_path)
