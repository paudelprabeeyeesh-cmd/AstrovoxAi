from __future__ import annotations

import click


@click.group()
def plugin() -> None:
    """Plugin management."""


@plugin.command()
@click.argument("plugin_id")
@click.option("--version", default="latest")
def install(plugin_id: str, version: str) -> None:
    click.echo(f"Installing plugin {plugin_id}@{version}")


@plugin.command()
@click.argument("plugin_id")
def uninstall(plugin_id: str) -> None:
    click.echo(f"Uninstalling plugin {plugin_id}")


@plugin.command()
def list() -> None:
    click.echo("Installed plugins:")
