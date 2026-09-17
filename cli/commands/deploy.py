from __future__ import annotations

import click


@click.group()
def deploy() -> None:
    """Deploy Astrovox services."""


@deploy.command()
@click.option("--env", default="development", help="Target environment")
@click.option("--tag", default="latest", help="Image tag")
def container(env: str, tag: str) -> None:
    click.echo(f"Deploying container {tag} to {env}")
