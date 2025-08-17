import rich_click as click

from bugninja_cli.add import add
from bugninja_cli.init import init
from bugninja_cli.replay import replay

from bugninja_cli.run import run
from bugninja_cli.stats import stats
from bugninja_cli.utils.style import MARKDOWN_CONFIG, display_logo


@click.group(invoke_without_command=True)
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.pass_context
def bugninja(ctx):
    # Display logo for all invocations
    display_logo()

    # If no command is specified, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


bugninja.add_command(add)
bugninja.add_command(init)
bugninja.add_command(run)
bugninja.add_command(replay)
bugninja.add_command(stats)

if __name__ == "__main__":
    bugninja()
