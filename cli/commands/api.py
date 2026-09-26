from __future__ import annotations

import click


@click.group()
def api() -> None:
    """API explorer and playground."""


@api.command()
@click.argument("endpoint")
@click.option("--method", default="GET")
@click.option("--body", default=None)
def call(endpoint: str, method: str, body: str) -> None:
    click.echo(f"Calling {method} {endpoint} with body {body}")


@api.command()
@click.argument("endpoint")
def docs(endpoint: str) -> None:
    click.echo(f"Fetching docs for {endpoint}")
