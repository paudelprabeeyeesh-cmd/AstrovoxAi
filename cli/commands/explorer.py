"""Live API explorer command for the CLI."""
from __future__ import annotations

import json

import click


@click.group()
def explorer() -> None:
    """Live API explorer."""


@explorer.command()
@click.option("--endpoint", default="/v1/chat/completions")
def browse(endpoint: str) -> None:
    """Browse an API endpoint interactively."""
    click.echo(f"Exploring {endpoint}")
    click.echo("Schema: (simulated)")
    click.echo(json.dumps(
        {
            "method": "POST",
            "path": endpoint,
            "parameters": [
                {"name": "model", "type": "string", "required": True},
                {"name": "messages", "type": "array", "required": True},
                {"name": "temperature", "type": "float", "required": False},
            ],
        },
        indent=2,
    ))


@explorer.command()
@click.option("--resource", default="conversations")
def list(resource: str) -> None:
    """List resources from the API."""
    click.echo(f"Listing {resource} (simulated)")
    click.echo(json.dumps([{"id": "1", "title": "Demo"}, {"id": "2", "title": "Example"}], indent=2))
