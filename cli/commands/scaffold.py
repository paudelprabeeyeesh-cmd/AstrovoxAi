from __future__ import annotations

import click


@click.group()
def scaffold() -> None:
    """Generate project scaffolding."""


@scaffold.command()
@click.argument("name")
@click.option("--template", default="service")
def service(name: str, template: str) -> None:
    click.echo(f"Scaffolding service '{name}' from template '{template}'")


@scaffold.command()
@click.argument("name")
@click.option("--template", default="plugin")
def plugin(name: str, template: str) -> None:
    click.echo(f"Scaffolding plugin '{name}' from template '{template}'")
