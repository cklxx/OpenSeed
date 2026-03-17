"""Shared CLI utilities."""

from __future__ import annotations

import click
from rich.console import Console

from openseed.config import OpenSeedConfig
from openseed.models.paper import Paper
from openseed.storage.library import PaperLibrary

console = Console()


def get_library(ctx: click.Context) -> PaperLibrary:
    return PaperLibrary(ctx.obj["config"].library_dir)


def get_config(ctx: click.Context) -> OpenSeedConfig:
    return ctx.obj["config"]


def require_paper(lib: PaperLibrary, paper_id: str) -> Paper:
    """Return paper or exit with error."""
    p = lib.get_paper(paper_id)
    if not p:
        console.print(f"[red]Paper {paper_id} not found.[/red]")
        raise SystemExit(1)
    return p
