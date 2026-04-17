import typer
from aspectcoder.cli.commands.run import run_command
from aspectcoder.cli.commands.status import status_command
from aspectcoder.cli.commands.rollback import rollback_command

app = typer.Typer(name="aspectcoder", help="Local multi-agent coding assistant.")

app.command("run")(run_command)
app.command("status")(status_command)
app.command("rollback")(rollback_command)
