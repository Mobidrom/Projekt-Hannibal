from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Generator, List, Mapping, Tuple

from hannibal.io.DBF import load_dbf
from hannibal.logging import LOGGER
from hannibal.providers.SEVAS.constants import SEVASZoneType
from hannibal.util.immutable import ImmutableMixin


class SEVASRoadSpeedType(str, Enum):
    """
    Members are listed in ascending order of allowed speed, so that the
    stricter value can be applied to an OSM way that matches multiple speed records.
    """

    # fußgängerzone
    PEDESTRIAN = "242.1"
    # verkehrsberuhigt
    CALM_TRAFFIC = "325.1"
    # tempo 20
    S20 = "274.1-20"
    # tempo 30
    S30 = "274.1"
    # geschlossene Ortschaft
    URBAN = "310"

    def __lt__(self, other):
        if self.__class__ is not other.__class__:
            raise TypeError(f"Can't compare {self.__class__} with {other.__class__}")

        # allow for comparison through member index
        members = list(SEVASRoadSpeedType.__members__.values())
        return members.index(self) < members.index(other)

    def __gt__(self, other):
        if self.__class__ is not other.__class__:
            raise TypeError(f"Can't compare {self.__class__} with {other.__class__}")

        # allow for comparison through member index
        members = list(SEVASRoadSpeedType.__members__.values())
        return members.index(self) > members.index(other)


SPEED_VALUES = {
    # 10 as a replacement for maxspeed=walk which is not supported by valhalla
    SEVASRoadSpeedType.PEDESTRIAN: "10",
    SEVASRoadSpeedType.CALM_TRAFFIC: "10",
    SEVASRoadSpeedType.S20: "20",
    SEVASRoadSpeedType.S30: "30",
    SEVASRoadSpeedType.URBAN: "50",
}

# OSM allows for a zone:traffic=* tag on ways and relations
ZONE_VALUES = {
    SEVASRoadSpeedType.CALM_TRAFFIC: "living_street",
    SEVASRoadSpeedType.S20: "zone20",
    SEVASRoadSpeedType.S30: "zone30",
    SEVASRoadSpeedType.URBAN: "urban",
}


@dataclass
class SEVASRoadSpeedRecord:
    segment_id: int
    zone_id: int
    name: str | None
    osm_vers: int
    osm_id: int
    typ: SEVASZoneType.SPEED
    wert: SEVASRoadSpeedType
    gemeinde: str
    kreis: str
    regbezirk: str

    def tags(self) -> Mapping[str, str]:
        """
        Get the OSM tags for this road segment.
        """
        tags = {"maxspeed": f"{self.get_speed()}"}
        if zone := self.get_zone():
            val = f"DE:{zone}"
            tags["zone:traffic"] = val
            tags["source:maxspeed"] = val
            tags["maxspeed:type"] = val
        return tags

    def get_speed(self) -> str:
        return SPEED_VALUES[self.wert]

    def get_zone(self) -> str | None:
        return ZONE_VALUES.get(self.wert)


def SevasRoadSpeedFactory(items: List[Tuple[str, Any]]) -> SEVASRoadSpeedRecord | None:
    """
    Factory function passed to the dbf loader to extract all the information we need
    from the zonal segment DBF. It contains low emission zone and speed type segments,
    but the LEM zone ones will be ignored here.

    :return: a record or None if it's a record we don't care about (i.e. low emission zone segments)
    """
    kwargs = {}
    for k, v in items:
        # we only care about the tempozonen
        if k == "typ" and v == "umweltzone":
            return None
        kwargs[k] = v

    return SEVASRoadSpeedRecord(**kwargs)


class SEVASRoadSpeeds(ImmutableMixin):
    def __init__(self, dbf_path: Path) -> None:
        """
        SEVAS preferred roads map. The DBF's records are read into memory at initialization by default.

        :param dbf: path to the restriction PBF file.
        """

        self._dbf_path = dbf_path

        # the mapping default value is an empty list
        self._map: Mapping[int, List[SEVASRoadSpeedRecord]] = defaultdict(list)

        # for stats, we keep track of the number of times an OSM ID was accessed
        self._access_count: Mapping[int, int] = {}

        dbf = load_dbf(dbf_path, SevasRoadSpeedFactory)

        record: SEVASRoadSpeedRecord

        for record in dbf.records:
            if record is None:
                continue
            self._map[record.osm_id].append(record)
            self._access_count[record.osm_id] = 0

        self.validate()

    def __getitem__(self, key: int) -> List[SEVASRoadSpeedRecord] | None:
        """
        Access the internal mapping by OSM ID
        """
        if val := self._map.get(key):
            self._access_count[key] += 1
            return val
        return None

    def unaccessed_osm_ids(self) -> Generator[int, Any, Any]:
        """
        Helps identify ways which were part of the passed DBF file but which were not
        present in the OSM file.
        """
        for k, v in self._access_count:
            if v == 0:
                yield k

    def items(self) -> Generator[Tuple[int, List[SEVASRoadSpeedRecord]], Any, Any]:
        """Underlying dict access."""
        for k, v in self._map.items():
            yield k, v

    def values(self) -> Generator[List[SEVASRoadSpeedRecord], Any, Any]:
        """Underlying dict access."""
        yield from self._map.values()

    def validate(self) -> bool:
        """
        Validate the road speed map: there can be multiple entries for an OSM ID, but
        only if each entry has a different type
        """

        for k, v in self.items():
            types = set()
            for speed in v:
                if speed.typ not in types:
                    types.add(speed.typ)
                else:
                    LOGGER.warning(f"Found duplicate speed types {speed.typ} in way {k}.")
                    return False

        return True
