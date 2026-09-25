from __future__ import annotations

import click


@click.group()
def test() -> None:
    """Run test suites."""


@test.command()
@click.option("--coverage/--no-coverage", default=True)
@click.option("--pattern", default="tests/**/*.py")
def run(coverage: bool, pattern: str) -> None:
    click.echo(f"Running tests matching {pattern} with coverage={coverage}")
