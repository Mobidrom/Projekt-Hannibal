from abc import ABC, ABCMeta, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Generator, Generic, List, Tuple

from osmium import TypeVar
from shapely import LineString

from hannibal.io.shapefile import load_shp


class SEVASBaseRecord(ABC):
    @abstractmethod
    def tags(self) -> Dict[str, str]:
        pass

    @property
    def __geo_interface__(self) -> Dict:
        """
        For interfacing neatly with geospatial Python libraries.
        See https://gist.github.com/sgillies/2217756
        """
        return {
            "type": "Feature",
            "properties": self.as_dict(),
            "geometry": {"type": "LineString", "coordinates": self.shape},
        }

    @property
    def geom(self) -> LineString:
        return LineString(self.shape)

    @abstractmethod
    def as_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


T = TypeVar("T", bound="SEVASBaseRecord")


class SEVASBaseTable(Generic[T], metaclass=ABCMeta):
    """
    Methods and properties that each SEVAS table needs to implement
    """

    def __init__(self, shp_path: Path) -> None:
        """
        SEVAS Layer. The shapefile's features are read into memory at initialization.

        :param shp_path: path to the layer's shapefile.
        """

        self._shp_path = shp_path

        # the mapping default value is an empty list
        self._map: Dict[int, List[T]] = defaultdict(list)

        # for stats, we keep track of the number of times an OSM ID was accessed
        self._access_count: Dict[int, int] = {}

        feature: T
        for feature in load_shp(shp_path, self.feature_factory):
            self._map[feature.osm_id].append(feature)
            self._access_count[feature.osm_id] = 0

    def __getitem__(self, key: int) -> List[T] | None:
        """
        Access the internal mapping by OSM ID
        """
        if self._access_count.get(key):
            self._access_count[key] += 1
        return self._map[key] or None

    def unaccessed_features(self) -> Generator[int, Any, Any]:
        """
        Returns the number of features that were not accessed during the conversion.
        Mostly interesting for full conversions, where the input OSM file was not bound to
        a subregion.
        """
        for k, v in self._access_count:
            if v == 0:
                yield k

    def items(self) -> Generator[Tuple[int, List[T]], Any, Any]:
        """
        Access the underlying features item-wise. Yields a tuple of (OSM ID, Feature).
        """
        for k, v in self._map.items():
            yield k, v

    def values(self) -> Generator[List[T], Any, Any]:
        """
        Access the underlying features.
        """
        yield from self._map.values()

    @property
    @abstractmethod
    def feature_factory(self):
        raise NotImplementedError

    @abstractmethod
    def invalidating_keys(self) -> Tuple[str]:
        raise NotImplementedError
