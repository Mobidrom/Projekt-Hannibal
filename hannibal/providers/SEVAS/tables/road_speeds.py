from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Mapping, Tuple

from hannibal.io.shapefile import FeatureLike
from hannibal.providers.SEVAS.constants import SEVASZoneType
from hannibal.providers.SEVAS.tables.base import SEVASBaseRecord, SEVASBaseTable


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
class SEVASRoadSpeedRecord(SEVASBaseRecord):
    segment_id: int
    zone_id: int
    name: str | None
    osm_vers: str
    osm_id: int
    typ: SEVASZoneType.SPEED
    wert: SEVASRoadSpeedType
    gemeinde: str
    kreis: str
    regbezirk: str
    shape: List[Tuple[float, float]]

    def as_dict(self) -> Mapping[str, str | int]:
        """
        Returns the road speed as a dictionary. Used for creating test data.
        """
        return {
            "segment_id": self.segment_id,
            "zone_id": self.zone_id,
            "name": self.name or "",
            "osm_vers": self.osm_vers,
            "osm_id": self.osm_id,
            "typ": self.typ.value,
            "wert": self.wert.value,
            "gemeinde": self.gemeinde,
            "kreis": self.kreis,
            "regbezirk": self.regbezirk,
        }

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

    @staticmethod
    def invalidating_keys() -> Tuple[str]:
        return SEVASRoadSpeeds.invalidating_keys()


class SEVASRoadSpeeds(SEVASBaseTable[SEVASRoadSpeedRecord]):
    def __init__(self, shp_path: Path) -> None:
        super().__init__(shp_path)

        # for road speeds, it's important to sort the list of entries for each OSM Way ID
        # from least to most strict, so that when tags are applied, the strictest ones wins
        for feature_list in self._map.values():
            feature_list.sort(key=lambda f: f.wert, reverse=True)

            print([f.wert for f in feature_list])

    @staticmethod
    def feature_factory(feature: FeatureLike) -> SEVASRoadSpeedRecord:
        """
        Factory function passed to the shapefile loader to extract all the information we need
        from the zonal segment shapefile. It contains low emission zone and speed type segments,
        but the LEM zone ones will be ignored here.

        :return: a record or None if it's a record we don't care about (i.e. low emission zone segments)
        """
        kwargs = {}
        for k, v in feature["properties"].items():
            # we only care about the tempozonen
            if k == "typ":
                if v == "umweltzone":
                    return None
                v = SEVASZoneType.SPEED
            if k == "wert":
                v = SEVASRoadSpeedType(v)
            kwargs[k] = v

        return SEVASRoadSpeedRecord(**kwargs, shape=feature["geometry"]["coordinates"])

    @staticmethod
    def invalidating_keys() -> Tuple[str]:
        return ("maxspeed", "maxspeed", "zone:traffic", "source:maxspeed")
