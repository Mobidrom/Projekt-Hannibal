import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Type

import numpy as np
from shapely import LineString, MultiPolygon, Point, Polygon, STRtree, unary_union

from hannibal.io.PolygonReader import PolygonReader
from hannibal.io.YAML import load_yaml
from hannibal.logging import LOGGER
from hannibal.providers import HannibalProvider

try:
    from typing import Self
except ImportError:
    from typing import TypeVar

    Self = TypeVar("Self")


@dataclass
class ProviderBaseConfig:
    clean: bool
    clean_tags: List[str] | None
    relation: int | None


@dataclass
class OsmBaseConfig:
    """Configure the OSM input."""

    path: Path | None
    url: str | None


@dataclass
class OutputConfig:
    """Configure the output."""

    path: Path


@dataclass
class HannibalConfig:
    """Class that holds the global configuration in memory"""

    providers: Mapping[HannibalProvider, ProviderBaseConfig]
    osm_base: OsmBaseConfig
    output: OutputConfig

    @classmethod
    def from_path(cls, p: Path) -> Type[Self]:
        conf = load_yaml(p)
        providers: Mapping[HannibalProvider, ProviderBaseConfig] = {}

        try:
            for prov, prov_dict in conf["providers"].items():
                provider_conf = ProviderBaseConfig(
                    prov_dict.get("clean_tags", {}).get("active") or False,
                    prov_dict.get("clean_tags", {}).get("tags"),
                    prov_dict.get("clean_tags", {}).get("area"),
                )
                providers[HannibalProvider(prov.lower())] = provider_conf

            osm_base_dict = conf["osm_base"]
            osm_base_conf = OsmBaseConfig(Path(osm_base_dict.get("path")), osm_base_dict.get("url"))

            output_config = OutputConfig(Path(conf["output"]["path"]))

            return cls(providers, osm_base_conf, output_config)

        except Exception as e:  # noqa
            raise ValueError(f"Error loading config from file: {e}")


@dataclass(frozen=True)
class TagCleanConfig:
    """
    Which tags to remove in which polygon. If exact is True, will only match exact keys,
    otherwise it will match all tag keys that start with any of the passed keys."""

    id: int
    keys: List[str]
    polygon: Polygon
    exact: bool = False

    def __post_init__(self):
        polys = self._evenly_split_polygons()
        super().__setattr__("_rtree", STRtree(polys))

    def spatial_check(self, other: Point | LineString) -> bool:
        """
        Checks whether the passed geometry intersects with the polygon. Internally, the polygon passed in
        the config is split into smaller sub-divisions and inserted into an R Tree for faster spatial
        queries.
        """
        result = self._rtree.query(other, "intersects")
        return bool(len(result))

    # adapted from https://github.com/gboeing/osmnx/blob/79b0dfccb6f2b8a196d0351b06e7081d62ed6bed/osmnx/utils_geo.py#L332
    def _evenly_split_polygons(self, square_size: float = 0.25, min_num: int = 3) -> List[Polygon]:
        """
        Split the passed polygon up into a specified number of sub-divisions.

        Returns at least (min_num + 1)^2 sub-polygons.

        :param geometry: the geometry to split up into smaller sub-polygons
        :param square_size: size of the square in same units as the original geometry
        :param min_num: the minimum number of lines in each dimension

        :return: a list of polygons
        """
        buffer = 1e-9

        west, south, east, north = self.polygon.bounds
        x_num = math.ceil((east - west) / square_size) + 1
        y_num = math.ceil((north - south) / square_size) + 1
        x_points = np.linspace(west, east, num=max(x_num, min_num))
        y_points = np.linspace(south, north, num=max(y_num, min_num))

        # create a grid of lines using evenly spaced points
        vertical_lines = [LineString([(x, y_points[0]), (x, y_points[-1])]) for x in x_points]
        horizontal_lines = [LineString([(x_points[0], y), (x_points[-1], y)]) for y in y_points]
        lines = vertical_lines + horizontal_lines

        # create a tiny bit of a buffer just to be sure
        buffer_size = square_size * buffer
        lines_buffered = [line.buffer(buffer_size) for line in lines]
        quadrats = unary_union(lines_buffered)
        multipoly: MultiPolygon = self.polygon.difference(quadrats)

        return list(multipoly.geoms)


def get_tag_clean_config(rel: int, osm_path: Path, keys: List[str]) -> TagCleanConfig:
    LOGGER.info(f"Reading spatial filter relation from OSM file {osm_path}")
    r = PolygonReader(rel)
    r.apply_file(str(osm_path))

    if not r.geometry:
        LOGGER.error(f"Unable to find area for relation {rel} in {osm_path}")
        return None

    return TagCleanConfig(rel, keys, r.geometry)
