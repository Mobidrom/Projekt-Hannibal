from pathlib import Path
from typing import Annotated

import typer
from rich import print

from hannibal.config.HannibalConfig import HannibalConfig

hannibal = typer.Typer()


@hannibal.command()
def convert(
    config: Annotated[Path, typer.Argument(help="The config to read from. Must be in YAML format.")],
):
    print(f"[bold]Starte [green]Hannibal Konversion[/green], lese Konfiguration von {config} [/bold]")
    hc = HannibalConfig.from_path(config)
    print(hc)
    print("Zu mehr bin ich gerade noch nicht in der Lage :-(")


def main():
    hannibal()
