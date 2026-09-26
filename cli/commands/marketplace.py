from __future__ import annotations

import click


@click.group()
def marketplace() -> None:
    """Plugin marketplace management."""


@marketplace.command()
@click.argument("plugin_id")
@click.option("--version", default="latest")
def install(plugin_id: str, version: str) -> None:
    click.echo(f"Installing plugin {plugin_id}@{version}")


@marketplace.command()
@click.argument("plugin_id")
def uninstall(plugin_id: str) -> None:
    click.echo(f"Uninstalling plugin {plugin_id}")


@marketplace.command()
def list() -> None:
    click.echo("Available plugins:")


@marketplace.command()
@click.argument("plugin_id")
def info(plugin_id: str) -> None:
    click.echo(f"Plugin info for {plugin_id}")


@marketplace.command()
@click.argument("path")
def publish(path: str) -> None:
    click.echo(f"Publishing plugin from {path}")
