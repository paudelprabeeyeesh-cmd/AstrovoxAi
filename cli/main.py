from __future__ import annotations

import click


@click.group()
@click.version_option(package_name="astrovox")
def cli() -> None:
    """Astrovox AI developer CLI."""


def register_commands() -> None:
    from cli.commands import deploy, debug, plugin, scaffold, test

    cli.add_command(deploy.deploy)
    cli.add_command(debug.debug)
    cli.add_command(plugin.plugin)
    cli.add_command(scaffold.scaffold)
    cli.add_command(test.test)


register_commands()


if __name__ == "__main__":
    cli()
