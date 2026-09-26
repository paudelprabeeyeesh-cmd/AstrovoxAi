from __future__ import annotations

import click


@click.group()
@click.version_option(package_name="astrovox")
def cli() -> None:
    """Astrovox AI developer CLI."""


def register_commands() -> None:
    from cli.commands import api, deploy, debug, developer, plugin, scaffold, test
    from cli.commands import analytics, explorer, playground

    cli.add_command(api.api)
    cli.add_command(deploy.deploy)
    cli.add_command(debug.debug)
    cli.add_command(developer.developer)
    cli.add_command(plugin.plugin)
    cli.add_command(scaffold.scaffold)
    cli.add_command(test.test)
    cli.add_command(analytics.analytics)
    cli.add_command(explorer.explorer)
    cli.add_command(playground.playground)


register_commands()


if __name__ == "__main__":
    cli()
