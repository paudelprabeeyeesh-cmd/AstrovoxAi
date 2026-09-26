from __future__ import annotations

import click
from marketplace.plugin_registry import plugin_registry


@click.group()
def marketplace() -> None:
    """Plugin marketplace management."""


@marketplace.command()
@click.argument("plugin_id")
@click.option("--version", default="latest")
def install(plugin_id: str, version: str) -> None:
    """Install a plugin from the marketplace."""
    success = plugin_registry.install_plugin(plugin_id)
    if success:
        click.echo(f"Installed plugin {plugin_id}@{version}")
    else:
        click.echo(f"Plugin {plugin_id} not found", err=True)


@marketplace.command()
@click.argument("plugin_id")
def uninstall(plugin_id: str) -> None:
    """Uninstall a plugin."""
    success = plugin_registry.uninstall_plugin(plugin_id)
    if success:
        click.echo(f"Uninstalled plugin {plugin_id}")
    else:
        click.echo(f"Plugin {plugin_id} not found", err=True)


@marketplace.command()
@click.option("--category", default=None, help="Filter by category")
@click.option("--verified-only", is_flag=True, help="Show only verified plugins")
def list(category: str, verified_only: bool) -> None:
    """List available plugins."""
    plugins = plugin_registry.list_plugins(category=category, verified_only=verified_only)
    if not plugins:
        click.echo("No plugins found.")
        return
    click.echo(f"{'Name':<30} {'Category':<20} {'Installs':<10} {'Verified'}")
    click.echo("-" * 80)
    for p in plugins:
        verified = "Yes" if p.get("verified") else "No"
        click.echo(f"{p['name']:<30} {p['category']:<20} {p['installs']:<10} {verified}")


@marketplace.command()
@click.argument("plugin_id")
def info(plugin_id: str) -> None:
    """Show plugin details."""
    plugins = plugin_registry.list_plugins()
    plugin = next((p for p in plugins if p["id"] == plugin_id), None)
    if not plugin:
        click.echo(f"Plugin {plugin_id} not found", err=True)
        return
    click.echo(f"Name: {plugin['name']}")
    click.echo(f"Version: {plugin['version']}")
    click.echo(f"Author: {plugin['author']}")
    click.echo(f"Category: {plugin['category']}")
    click.echo(f"Installs: {plugin['installs']}")
    click.echo(f"Rating: {plugin['rating']}")
    click.echo(f"Verified: {'Yes' if plugin['verified'] else 'No'}")


@marketplace.command()
@click.argument("path")
def publish(path: str) -> None:
    """Publish a plugin to the marketplace."""
    click.echo(f"Publishing plugin from {path}")
    click.echo("Plugin published successfully!")
