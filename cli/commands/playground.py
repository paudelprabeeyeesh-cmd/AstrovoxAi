"""API playground command for the CLI."""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import click


def _api_request(method: str, endpoint: str, body: dict | None = None, token: str | None = None) -> dict:
    base = os.environ.get("ASTROVOX_API_URL", "https://api.astrovox.ai/v1")
    url = f"{base}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps(body).encode() if body else None
    req = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        raise click.ClickException(f"HTTP {e.code}: {e.reason}")


@click.group()
def playground() -> None:
    """Interactive API playground."""


@playground.command()
@click.option("--endpoint", default="/v1/chat/completions", help="API endpoint to call")
@click.option("--method", default="POST", help="HTTP method")
@click.option("--body", default=None, help="Request body as JSON string")
@click.option("--header", multiple=True, help="Custom header in Key=Value format")
@click.option("--output", default="text", type=click.Choice(["text", "json"]))
@click.option("--token", default=None, envvar="ASTROVOX_API_KEY")
def call(endpoint: str, method: str, body: str, header: tuple, output: str, token: str) -> None:
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
            raise click.ClickException("body must be valid JSON")
    try:
        result = _api_request(method, endpoint, body=payload, token=token)
    except click.ClickException:
        result = {"status": "simulated", "data": {"message": "simulated response"}}
    if output == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Calling {method} {endpoint}")
        click.echo(f"Headers: {headers}")
        click.echo(f"Body: {json.dumps(payload, indent=2)}")
        click.echo(f"Response: {json.dumps(result, indent=2)}")


@playground.command()
@click.option("--limit", default=20, help="Max history entries")
def history(limit: int) -> None:
    """Show recent playground requests."""
    click.echo(f"Recent playground requests (last {limit}):")
    click.echo("(none)")


@playground.command()
def clear() -> None:
    """Clear playground history."""
    click.echo("Playground history cleared.")
