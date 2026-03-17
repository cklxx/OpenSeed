"""Experiment tracking commands."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from openseed.cli._helpers import get_library
from openseed.models.experiment import Experiment

console = Console()


@click.group()
@click.pass_context
def experiment(ctx: click.Context) -> None:
    """Track experiments."""
    ctx.ensure_object(dict)


@experiment.command()
@click.argument("paper_id")
@click.argument("name")
@click.option("--repo", help="Git repository URL")
@click.option("--description", "-d", default="", help="Experiment description")
@click.pass_context
def link(ctx: click.Context, paper_id: str, name: str, repo: str | None, description: str) -> None:
    """Link a new experiment to a paper."""
    lib = get_library(ctx)
    if not lib.get_paper(paper_id):
        console.print(f"[red]Paper {paper_id} not found.[/red]")
        raise SystemExit(1)
    exp = Experiment(name=name, paper_id=paper_id, repo_url=repo, description=description)
    lib.add_experiment(exp)
    console.print(f"[green]✓[/green] Linked experiment [bold]{name}[/bold] to paper {paper_id}")


@experiment.command("list")
@click.option("--paper-id", help="Filter by paper ID")
@click.pass_context
def list_experiments(ctx: click.Context, paper_id: str | None) -> None:
    """List experiments."""
    lib = get_library(ctx)
    experiments = lib.list_experiments()
    if paper_id:
        experiments = [e for e in experiments if e.paper_id == paper_id]
    if not experiments:
        console.print("[dim]No experiments found.[/dim]")
        return
    table = Table(title="Experiments")
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Name", style="bold")
    table.add_column("Paper", width=12)
    table.add_column("Runs", justify="right")
    for exp in experiments:
        table.add_row(exp.id, exp.name, exp.paper_id, str(len(exp.runs)))
    console.print(table)


@experiment.command()
@click.argument("experiment_id")
@click.pass_context
def show(ctx: click.Context, experiment_id: str) -> None:
    """Show experiment details."""
    lib = get_library(ctx)
    exp = lib.get_experiment(experiment_id) or lib.get_experiment_by_name(experiment_id)
    if not exp:
        console.print(f"[red]Experiment {experiment_id} not found.[/red]")
        raise SystemExit(1)
    lines = [
        f"[bold]Name:[/bold] {exp.name}",
        f"[bold]Paper:[/bold] {exp.paper_id}",
        f"[bold]Repo:[/bold] {exp.repo_url or 'N/A'}",
        f"[bold]Runs:[/bold] {len(exp.runs)}",
    ]
    if exp.description:
        lines += ["", f"[bold]Description:[/bold]\n{exp.description}"]
    console.print(Panel("\n".join(lines), title=f"Experiment {exp.id}", border_style="green"))
