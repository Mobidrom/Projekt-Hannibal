from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, List, Mapping, Tuple

from hannibal.io.shapefile import FeatureLike, load_shp
from hannibal.providers import HannibalProvider
from hannibal.providers.SEVAS.constants import SEVASDir
from hannibal.util.exception import HannibalSchemaError
from hannibal.util.immutable import ImmutableMixin


@dataclass
class SEVASPreferredRoadRecord:
    osm_id: int
    fahrtri: SEVASDir
    shape: List[Tuple[float, float]]

    def as_dict(self) -> Mapping[str, str | int]:
        """
        Get the record as a dictionary
        """
        return {"osm_id": self.osm_id, "fahrtri": self.fahrtri.value}

    @property
    def __geo_interface__(self):
        return {
            "type": "Feature",
            "properties": {"osm_id": self.osm_id, "fahrtri": self.fahrtri},
            "geometry": {"type": "LineString", "coordinates": self.shape},
        }

    def tag(self) -> Mapping[str, str]:
        """
        Get the OSM tag for this preferred road segment.
        """
        return {f"hgv{self._get_direction()}": "designated"}

    def _get_direction(self):
        """
        Generate a direction namespace suffix for the OSM tag key.
        """
        match self.fahrtri:
            case SEVASDir.BOTH:
                return ""
            case SEVASDir.FORW:
                return ":forward"
            case SEVASDir.BACKW:
                return ":backward"
            case _:
                raise HannibalSchemaError("fahrtri", str(self.fahrtri), HannibalProvider.SEVAS)


def SevasPreferredRoadFactory(feature: FeatureLike) -> SEVASPreferredRoadRecord:
    """
    Factory function passed to the dbf loader to extract all the information we need
    from the preferred road DBF (Dt. Vorrangrouten).

    :return: returns a record
    """

    id_: int = feature["properties"]["osm_id"]
    dir_: SEVASDir = SEVASDir(feature["properties"]["fahrtri"])

    return SEVASPreferredRoadRecord(id_, dir_, feature["geometry"]["coordinates"])


class SEVASPreferredRoads(ImmutableMixin):
    def __init__(self, shp_path: Path) -> None:
        """
        SEVAS preferred roads map. The shapefile's features are read into memory at initialization.

        :param shp_path: path to the restriction Shapefile.
        """

        self._shp_path = shp_path

        # the mapping default value is an empty list
        self._map: Mapping[int, List[SEVASPreferredRoadRecord]] = defaultdict(list)

        # for stats, we keep track of the number of times an OSM ID was accessed
        self._access_count: Mapping[int, int] = {}

        feature: SEVASPreferredRoadRecord
        for feature in load_shp(shp_path, SevasPreferredRoadFactory):
            self._map[feature.osm_id].append(feature)
            self._access_count[feature.osm_id] = 0

    def __getitem__(self, key: int) -> SEVASPreferredRoadRecord | None:
        """
        Access the internal mapping by OSM ID
        """
        if v := self._map.get(key):
            self._access_count[key] += 1
            return v

    def unaccessed_osm_ids(self) -> Generator[int, Any, Any]:
        for k, v in self._access_count:
            if v == 0:
                yield k

    def items(self) -> Generator[Tuple[int, SEVASPreferredRoadRecord], Any, Any]:
        for k, v in self._map.items():
            yield k, v

    def values(self) -> Generator[SEVASPreferredRoadRecord, Any, Any]:
        yield from self._map.values()
