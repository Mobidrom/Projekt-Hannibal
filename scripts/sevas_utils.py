import sys
from pathlib import Path
from typing import Annotated

import typer
from rich import print

from hannibal.config.HannibalConfig import TagCleanConfig, get_tag_clean_config
from hannibal.io.PolygonReader import PolygonReader
from hannibal.providers.SEVAS.client import SEVASClient
from hannibal.providers.SEVAS.provider import SEVASProvider

sys.path.append("../hannibal")
sys.path.append("../")
sys.path.append("./")

# noqa
from hannibal.logging import LOGGER, LogLevel, init_logger

app = typer.Typer()


@app.command()
def download(
    data_dir: Path,
    base_url: Annotated[str, typer.Argument(help="")] = "https://sevas.nrw.de/osm/sevas",
    log_level: Annotated[LogLevel, typer.Option(help="Logging level")] = LogLevel.WARN,
):
    """
    Lädt alle SEVAS Datensätze in das angegebene Verzeichnis herunter.
    """
    init_logger(log_level)
    client = SEVASClient(data_dir, base_url)
    client.get_all()


@app.command()
def convert(
    data_dir: Annotated[
        Path, typer.Argument(help="Das Directory, in dem sich die SEVAS Daten befinden")
    ],
    osm_in: Annotated[
        Path, typer.Argument(help="Der Pfad zur OSM Datei, die als Grundlage zur Konvertierung dient")
    ],
    osm_out: Annotated[
        Path,
        typer.Argument(
            help="Der Pfad inkl. Dateiname, an dem die resultierende OSM Datei abgelegt wird"
        ),
    ],
    base_url: Annotated[
        str, typer.Argument(help="Die Basis URL des SEVAS Web Feature Service")
    ] = "https://sevas.nrw.de/osm/sevas",
    clean_area: Annotated[
        int,
        typer.Option(
            help="Die Relation ID eines Polygons, in dem bestimmte Tags entfernt werden sollen"
        ),
    ] = -1,
    clean_tags: Annotated[
        str, typer.Option(help="Die Tags, die herausgefiltert werden sollen (durch Kommata separiert)")
    ] = "",
    log_level: Annotated[LogLevel, typer.Option(help="Logging level")] = LogLevel.WARN,
    collect_unmatched_features: Annotated[
        bool,
        typer.Option(help="Sollen Segmente, die nicht gematched werden konnten, ausgegeben werden?"),
    ] = False,
):
    """
    Konvertierung von SEVAS zu OSM.
    """
    init_logger(log_level)
    print("[bold]Starte SEVAS Konvertierung.[/bold]")

    t: TagCleanConfig | None = None
    try:
        tags = [s.strip() for s in clean_tags.split(",")]
    except:  # noqa
        raise ValueError("Tags müssen durch Kommmata getrennte Werte sein.")

    if clean_area > -1:
        t = get_tag_clean_config(clean_area, osm_in, tags)
    else:
        if len(clean_tags):
            LOGGER.warn("Filter Tags wurden angegeben, aber keine gültige Relation ID.")
    provider = SEVASProvider(osm_in, osm_out, base_url, data_dir, False, tag_clean_config=t)
    provider.process()
    provider.report()

    if collect_unmatched_features:
        print("Ungematchte Segmente:")
        for k, v in provider.unmatched_features():
            print(f"{k}:")
            for id_ in v:
                print(id_)


@app.command()
def get_polygon(
    path: Annotated[Path, typer.Argument(help="Pfad zu OSM Datei")],
    id: Annotated[int, typer.Argument(help="Relation oder Way ID")],
):
    r = PolygonReader(id)
    r.apply_file(str(path), locations=True, idx="flex_mem")
    print(r.geometry.geoms[0])

if __name__ == "__main__":
    app()
