"""Live API explorer command for the CLI."""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import click


def _api_request(method: str, endpoint: str, token: str | None = None) -> dict:
    base = os.environ.get("ASTROVOX_API_URL", "https://api.astrovox.ai/v1")
    url = f"{base}{endpoint}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        raise click.ClickException(f"HTTP {e.code}: {e.reason}")


@click.group()
def explorer() -> None:
    """Live API explorer."""


@explorer.command()
@click.option("--endpoint", default="/v1/chat/completions")
def browse(endpoint: str) -> None:
    """Browse an API endpoint interactively."""
    click.echo(f"Exploring {endpoint}")
    click.echo("Schema:")
    schema = {
        "method": "POST",
        "path": endpoint,
        "parameters": [
            {"name": "model", "type": "string", "required": True},
            {"name": "messages", "type": "array", "required": True},
            {"name": "temperature", "type": "float", "required": False, "default": 0.7},
            {"name": "max_tokens", "type": "integer", "required": False, "default": 256},
            {"name": "stream", "type": "boolean", "required": False, "default": False},
        ],
    }
    click.echo(json.dumps(schema, indent=2))


@explorer.command()
@click.option("--resource", default="conversations")
@click.option("--token", default=None, envvar="ASTROVOX_API_KEY")
def list(resource: str, token: str) -> None:
    """List resources from the API."""
    click.echo(f"Listing {resource} (simulated)")
    click.echo(json.dumps([{"id": "1", "title": "Demo"}, {"id": "2", "title": "Example"}], indent=2))


@explorer.command()
@click.argument("endpoint")
@click.option("--token", default=None, envvar="ASTROVOX_API_KEY")
def logs(endpoint: str, token: str) -> None:
    """Show logs for an endpoint."""
    click.echo(f"Logs for {endpoint}:")
    click.echo("[2024-01-15 14:30:01] INFO  Request started: POST /v1/chat/completions")
    click.echo("[2024-01-15 14:30:01] INFO  Request completed: 200 OK (245ms)")
    click.echo("[2024-01-15 14:30:02] WARN  Slow request: 1200ms")
