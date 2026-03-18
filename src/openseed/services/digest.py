"""Digest generation — markdown summary of new papers from watch runs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from openseed.models.paper import Paper


def generate_digest(
    watch_results: dict[str, list[Paper]],
    watch_names: dict[str, str],
) -> str:
    """Generate a markdown digest from watch results."""
    now = datetime.now(UTC)
    lines = [f"# OpenSeed Digest — {now:%Y-%m-%d}\n"]
    total = sum(len(papers) for papers in watch_results.values())
    if total == 0:
        lines.append("No new papers found.\n")
        return "\n".join(lines)

    lines.append(f"**{total} papers** found across {len(watch_results)} watches.\n")

    for watch_id, papers in watch_results.items():
        query = watch_names.get(watch_id, watch_id)
        lines.append(f"\n## {query}\n")
        if not papers:
            lines.append("No results.\n")
            continue
        for p in papers:
            authors = ", ".join(a.name for a in p.authors[:3]) if p.authors else "Unknown"
            lines.append(f"- **{p.title}** — {authors} (`{p.arxiv_id or 'N/A'}`)")

    return "\n".join(lines) + "\n"


def save_digest(content: str, digest_dir: Path) -> Path:
    """Write digest to a timestamped markdown file."""
    digest_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    path = digest_dir / f"digest_{now:%Y%m%d_%H%M}.md"
    path.write_text(content, encoding="utf-8")
    return path
