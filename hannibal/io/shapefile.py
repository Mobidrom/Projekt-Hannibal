from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Tuple, TypedDict, TypeVar

import fiona

from hannibal.util.exception import HannibalIOError

T = TypeVar("T")


class PointLike(TypedDict):
    type: str = "Point"
    coordinates: Tuple[float, float]


class LineStringLike(TypedDict):
    type: str = "LineString"
    coordinates: List[Tuple[float, float]]


class PolygonLike(TypedDict):
    type: str = "Polygon"
    coordinates: List[List[Tuple[float, float]]]


class FeatureLike(TypedDict):
    properties: Dict[str, str | int | None]
    geometry: PointLike | LineStringLike | PolygonLike


def load_shp(p: Path, feature_factory: Callable[[Any], T]) -> Generator[T, Any, Any]:
    """
    Loads a shapefile and returns a generator of the passed factory return type.

    :param p: the path to the shapefile (.shp)
    :param feature_factory: a callable that takes a feature read from the shapefile and returns an
        object derived from that feature (e.g. a data class)
    """

    try:
        with fiona.open(p) as shp:
            for feature in shp:
                yield feature_factory(feature)
    except Exception as e:  # noqa
        raise HannibalIOError(f"Failed to load shapefile at {p}: {e}")
