from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
@click.option("--output", default="text", type=click.Choice(["text", "json"]))
def list(category: str, verified_only: bool, output: str) -> None:
    """List available plugins."""
    plugins = plugin_registry.list_plugins(category=category, verified_only=verified_only)
    if not plugins:
        click.echo("No plugins found.")
        return
    if output == "json":
        click.echo(json.dumps(plugins, indent=2))
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
@click.option("--category", default=None)
def publish(path: str, category: str) -> None:
    """Publish a plugin to the marketplace."""
    plugin_path = Path(path)
    manifest_path = plugin_path / "manifest.json"
    if not manifest_path.exists():
        click.echo(f"manifest.json not found in {path}", err=True)
        raise click.Abort()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin = plugin_registry.register_plugin(
        name=manifest.get("name", plugin_path.name),
        version=manifest.get("version", "0.1.0"),
        description=manifest.get("description", ""),
        author=manifest.get("author", "unknown"),
        category=category or manifest.get("category", "general"),
        manifest=manifest,
    )
    click.echo(f"Published plugin {plugin.name}@{plugin.version} to marketplace")

