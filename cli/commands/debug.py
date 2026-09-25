from __future__ import annotations

import click


@click.group()
def debug() -> None:
    """Debug and diagnostics."""


@debug.command()
@click.option("--session-id", required=True)
def trace(session_id: str) -> None:
    click.echo(f"Tracing session {session_id}")


@debug.command()
@click.option("--component", required=True)
def profile(component: str) -> None:
    click.echo(f"Profiling {component}")
