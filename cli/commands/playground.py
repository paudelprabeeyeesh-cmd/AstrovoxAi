"""API playground command for the CLI."""
from __future__ import annotations

import click
import json


@click.group()
def playground() -> None:
    """Interactive API playground."""


@playground.command()
@click.option("--endpoint", default="/v1/chat/completions", help="API endpoint to call")
@click.option("--method", default="POST", help="HTTP method")
@click.option("--body", default=None, help="Request body as JSON string")
@click.option("--header", multiple=True, help="Custom header in Key=Value format")
@click.option("--output", default="text", type=click.Choice(["text", "json"]), help="Output format")
def call(endpoint: str, method: str, body: str, header: tuple, output: str) -> None:
    """Send a request to the API playground."""
    headers = {}
    for h in header:
        if "=" in h:
            k, v = h.split("=", 1)
            headers[k] = v
    payload = {}
    if body:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            click.echo("Error: body must be valid JSON", err=True)
            raise click.Abort()
    click.echo(f"Calling {method} {endpoint}")
    click.echo(f"Headers: {headers}")
    click.echo(f"Body: {json.dumps(payload, indent=2)}")
    click.echo("Response: (simulated)")
    click.echo(json.dumps({"status": "ok", "data": {"message": "simulated response"}}, indent=2))


@playground.command()
def history() -> None:
    """Show recent playground requests."""
    click.echo("Recent playground requests: (none)")


@playground.command()
def clear() -> None:
    """Clear playground history."""
    click.echo("Playground history cleared.")
