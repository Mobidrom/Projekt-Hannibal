from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Generator, List

from osmium.osm import Tag as OsmiumTag

from hannibal.io.shapefile import load_shp
from hannibal.providers.SEVAS.constants import SEVASZoneType
from hannibal.util.immutable import ImmutableMixin

MAX_OBJ_ID = 2**63 - 1


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
        max_node_id: int = MAX_OBJ_ID,
        max_way_id: int = MAX_OBJ_ID,
        max_rel_id: int = MAX_OBJ_ID,
    ) -> None:
        """
        SEVAS low emission zones map.

        In order not to corrupt or overwrite existing OSM objects, new object IDs are generated starting
        from the highest possible value (2**63 - 1 for signed 64-bit integers) by default. If new objects
        are to be created from various threads and stored in the same OSM file, each thread needs to
        reserve an ID space. This can be achieved through the max_*_id arguments. Just make sure to
        reserve enough possible IDs for each thread.

        :param shp: path to the polygon shapefile.
        :param max_node_id: the maximum node ID to begin decrementing from
        :param max_way_id: the maximum way ID to begin decrementing from
        :param max_rel_id: the maximum relation ID to begin decrementing from
        """

        self._shp_path = shp_path
        self._max_node_id = max_node_id
        self._max_way_id = max_way_id
        self._max_rel_id = max_rel_id

    def features(self) -> Generator[SEVAS_LEZ_Record, Any, Any]:
        """
        Returns a generator that reads features from the shapefile.
        """
        for f in load_shp(self._shp_path, SevasLEZFactory):
            if f:
                yield f
