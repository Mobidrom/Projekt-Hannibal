from pathlib import Path
from typing import Any, Callable, Generator, TypeVar

import fiona

from hannibal.util.exception import HannibalIOError

T = TypeVar("T")


def load_shp(p: Path, feature_factory: Callable[[Any], T]) -> Generator[T, Any, Any]:
    """
    Loads a shapefile and returns a generator of the passed factory return type.

    :param p: the path to the shapefile (.shp)
    :param feature_factory: a callable that takes a feature read from the shapefile and returns an
        object derived from that feature (e.g. a data class)
    """

    try:
        with fiona.open(p, encoding="utf-8") as shp:
            for feature in shp:
                yield feature_factory(feature)
    except Exception as e:  # noqa
        raise HannibalIOError(f"Failed to load shapefile at {p}: {e}")
