import sys
from collections import defaultdict
from enum import Enum
from logging import DEBUG
from pathlib import Path
from typing import Annotated

import typer

sys.path.append("../hannibal")
sys.path.append("../")
sys.path.append("./")
# noqa
from hannibal.logging import init_logger
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions

app = typer.Typer()
init_logger(DEBUG)


class SEVASType(str, Enum):
    RESTRICTIONS = "restrictions"
    SIGNS = "signs"
    POLYGONS = "polygons"
    POLY_SEGMENTS = "poly_segments"


@app.command()
def uniquecounts(
    path: Path,
    type: Annotated[SEVASType, typer.Option(help="The type of features")] = SEVASType.RESTRICTIONS,
    cutoff: Annotated[int, typer.Option(help="Count threshold")] = 0,
    attr: Annotated[str, typer.Option(help="The attribute to count")] = "",
):
    if type is not SEVASType.RESTRICTIONS:
        raise NotImplementedError

    all_restrictions = SEVASRestrictions(path)
    types = defaultdict(int)

    for osm_id, restrs in all_restrictions.items():
        for res in restrs:
            try:
                types[getattr(res, attr)] += 1
            except AttributeError:
                raise AttributeError(f"Attribute {attr} does not exist on type {res.__class__.__name__}")

    sorted_types = sorted(types.items(), key=lambda i: i[1], reverse=True)
    print(f"{attr.capitalize()},COUNT")
    for k, v in sorted_types:
        if cutoff and v < cutoff:
            break
        print(f"{k},{v}")


@app.command()
def tags(
    path: Path,
    type: Annotated[SEVASType, typer.Option(help="The type of features")] = SEVASType.RESTRICTIONS,
):
    if type is not SEVASType.RESTRICTIONS:
        raise NotImplementedError

    all_restrictions = SEVASRestrictions(path)

    for osm_id, restrs in all_restrictions.items():
        print(f"OSM ID: {osm_id}")
        for rest in restrs:
            print(f"\tRestriction: {rest.restrkn_id}")
            print(f"\tSegment: {rest.segment_id}")
            for tag in rest.tags():
                print(f'\t\t"{tag.k}": "{tag.v}"')


@app.command()
def by_id(
    path: Path,
    id: Annotated[int, typer.Option(help="Segment_ID")] = 0,
    type: Annotated[SEVASType, typer.Option(help="The type of features")] = SEVASType.RESTRICTIONS,
):
    if type is not SEVASType.RESTRICTIONS:
        raise NotImplementedError

    all_restrictions = SEVASRestrictions(path)

    for osm_id, restrs in all_restrictions.items():
        for rest in restrs:
            if rest.segment_id == id:
                print(rest)


def main():
    app()


if __name__ == "__main__":
    main()
