import rich_click as click

from bugninja_cli.add import add
from bugninja_cli.init import init
from bugninja_cli.replay import replay
from bugninja_cli.run import run

# from bugninja_cli.stats import stats
from bugninja_cli.utils.style import MARKDOWN_CONFIG, display_logo

# class OrderedGroup(click.Group):
#     def __init__(
#         self,
#         name: Optional[str] = None,
#         commands: Optional[Mapping[str, click.Command]] = None,
#         **kwargs,
#     ):
#         super(OrderedGroup, self).__init__(name, commands, **kwargs)
#         #: the registered subcommands by their exported names.
#         self.commands = commands or OrderedDict()

#     def list_commands(self, ctx: click.Context) -> Mapping[str, click.Command]:
#         return self.commands


@click.group(invoke_without_command=True)
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.pass_context
def bugninja(ctx):
    # Display logo for all invocations
    display_logo()

    # If no command is specified, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


bugninja.add_command(init)
bugninja.add_command(add)
bugninja.add_command(run)
bugninja.add_command(replay)
# TODO! later
# bugninja.add_command(stats)

if __name__ == "__main__":
    bugninja()
