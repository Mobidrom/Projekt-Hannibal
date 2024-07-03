import sys
from enum import Enum
from logging import DEBUG
from pathlib import Path
from typing import Annotated, List

import typer

from hannibal.config.HannibalConfig import TagCleanConfig, get_tag_clean_config
from hannibal.io.PolygonReader import PolygonReader
from hannibal.providers.SEVAS.client import SEVASClient
from hannibal.providers.SEVAS.provider import SEVASProvider

sys.path.append("../hannibal")
sys.path.append("../")
sys.path.append("./")

# noqa
from hannibal.logging import LOGGER, init_logger
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions

app = typer.Typer()
init_logger(DEBUG)


class SEVASType(str, Enum):
    RESTRICTIONS = "restrictions"
    SIGNS = "signs"
    POLYGONS = "polygons"
    POLY_SEGMENTS = "poly_segments"


@app.command()
def tags(
    path: Path,
    type: Annotated[SEVASType, typer.Option(help="The type of features")] = SEVASType.RESTRICTIONS,
):
    """
    Tool zum Anzeigen konvertierter OSM Tags auf Basis eines SEVAS Datensatzes. Unterstützt zur Zeit nur
    Restriktionen
    """
    if type is not SEVASType.RESTRICTIONS:
        raise NotImplementedError

    all_restrictions = SEVASRestrictions(path)

    for osm_id, restrs in all_restrictions.items():
        print(f"OSM ID: {osm_id}")
        for rest in restrs:
            print(f"\tRestriction: {rest.restrkn_id}")
            print(f"\tSegment: {rest.segment_id}")
            for k, v in rest.tags().items():
                print(f'\t\t"{k}": "{v}"')


@app.command()
def download(
    data_dir: Path,
    base_url: Annotated[str, typer.Argument(help="")] = "https://sevas.nrw.de/osm/sevas",
):
    """
    Lädt alle SEVAS Datensätze herunter.
    """
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
    filter_relation: Annotated[
        int,
        typer.Option(
            help="Die Relation ID eines Polygons, in dem bestimmte Tags herausgefiltert werden sollen"
        ),
    ] = -1,
    filter_tags: Annotated[
        List[str], typer.Option("-t", help="Die Tags, die herausgefiltert werden sollen")
    ] = [],
):
    """
    Konvertierung von SEVAS zu OSM.
    """
    t: TagCleanConfig | None = None
    if filter_relation > -1:
        t = get_tag_clean_config(filter_relation, osm_in, filter_tags)
    else:
        if len(filter_tags):
            LOGGER.warn("Filter Tags wurden angegeben, aber keine gültige Relation ID.")
    provider = SEVASProvider(osm_in, osm_out, base_url, data_dir, False, tag_clean_config=t)
    provider.process()
    provider.report()


@app.command()
def by_id(
    path: Path,
    id: Annotated[int, typer.Option(help="Segment ID")] = 0,
    type: Annotated[SEVASType, typer.Option(help="")] = SEVASType.RESTRICTIONS,
):
    """
    Tool zum Inspizieren einzelner SEVAS Features (unterstützt zur Zeit nur Restriktionen)
    """
    if type is not SEVASType.RESTRICTIONS:
        raise NotImplementedError

    all_restrictions = SEVASRestrictions(path)

    for osm_id, restrs in all_restrictions.items():
        for rest in restrs:
            if rest.segment_id == id:
                print(rest)


@app.command()
def get_polygon(
    path: Annotated[Path, typer.Argument(help="Pfad zu OSM Datei")],
    id: Annotated[int, typer.Argument(help="Relation oder Way ID")],
):
    r = PolygonReader(id)
    r.apply_file(str(path), locations=True, idx="flex_mem")
    print(r.geometry.geoms[0])


def main():
    app()


if __name__ == "__main__":
    main()
