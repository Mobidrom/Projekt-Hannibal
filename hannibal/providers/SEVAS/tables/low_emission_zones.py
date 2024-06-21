from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Generator, List

from osmium.osm import Tag as OsmiumTag

from hannibal.io.shapefile import load_shp
from hannibal.providers.SEVAS.constants import SEVASZoneType
from hannibal.util.immutable import ImmutableMixin


class SEVASLEZType(str, Enum):
    """
    The type of low emission zone.
    """

    GREEN = "1031-52"
    YELLOW = "1031-51"
    RED = "1031-50"


@dataclass
class SEVAS_LEZ_Record:
    zone_id: int
    typ: SEVASZoneType.SPEED
    wert: SEVASLEZType
    gemeinde: str
    kreis: str
    regbezirk: str
    shape: List[List[List[int]]]

    def tag(self) -> List[OsmiumTag]:
        """
        Get the OSM tags for the low emission zone relation.
        """
        return OsmiumTag("boundary", "low_emission_zone")


def SevasLEZFactory(feature: Any) -> SEVAS_LEZ_Record | None:
    """
    Factory function passed to the shp loader to extract all the information we need
    from the zone (i.e. polygon) shapefile. It contains low emission zone and speed type segments,
    but the speed zones will be ignored here (we use the segments/roads layer for that).

    :return: a record or none if the zone type does not match up
    """

    props = feature["properties"]

    if props["typ"] != SEVASZoneType.LEM.value:
        return None

    return SEVAS_LEZ_Record(
        props["zone_id"],
        SEVASZoneType(props["typ"]),
        SEVASLEZType(props["wert"]),
        props["gemeinde"],
        props["kreis"],
        props["regbezirk"],
        feature["geometry"]["coordinates"],
    )


class SEVAS_LEZ(ImmutableMixin):
    def __init__(
        self,
        shp_path: Path,
    ) -> None:
        """
        SEVAS low emission zones map.


        :param shp: path to the polygon shapefile.
        """

        self._shp_path = shp_path

    def features(self) -> Generator[SEVAS_LEZ_Record, Any, Any]:
        """
        Returns a generator that reads features from the shapefile.
        """
        for f in load_shp(self._shp_path, SevasLEZFactory):
            if f:
                yield f
