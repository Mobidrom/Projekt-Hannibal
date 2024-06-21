from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, List, Tuple

from hannibal.io.DBF import load_dbf
from hannibal.io.shapefile import load_shp
from hannibal.util.immutable import ImmutableMixin

MAX_SIGN_NODE_ID = 2**62


@dataclass
class SEVASSignRecord:
    a_id: int
    schild_id: int
    typ: str
    wert: str
    normalenri: int | None
    gemeinde: str
    kreis: str
    regbezirk: str
    shape: Tuple[int, int]


def _ID_Factory(items: List[Tuple[str, Any]]) -> int:
    """
    Helper to read unique a_id values.
    """
    for name, value in items:
        if name == "a_id":
            return value


def SevasSignRecordFactory(feature: Any) -> SEVASSignRecord:
    """
    Factory function passed to the shp loader to extract all the information we need
    from the traffic sign shapefile.
    """

    props = feature["properties"]
    return SEVASSignRecord(
        props["a_id"],
        props["schild_id"],
        props["typ"],
        props["wert"],
        props["normalenri"],
        props["gemeinde"],
        props["kreis"],
        props["regbezirk"],
        feature["geometry"]["coordinates"],
    )


class SEVASSigns(ImmutableMixin):
    def __init__(
        self,
        shp_path: Path,
        max_node_id: int = MAX_SIGN_NODE_ID,
    ) -> None:
        """
        SEVAS traffic signs.

        In order not to corrupt or overwrite existing OSM objects, new object IDs are generated starting
        from high values (max is 2**63 - 1 for signed 64-bit integers) by default. If new objects
        are to be created from various threads and stored in the same OSM file, each thread needs to
        reserve an ID space. This can be achieved through the max_*_id arguments. Just make sure to
        reserve enough possible IDs for each thread.

        :param shp: path to the polygon shapefile.
        :param max_node_id: the maximum node ID to begin decrementing from
        """

        self._shp_path = shp_path
        self._max_node_id = max_node_id

        self._unique_a_ids = []
        for rec in load_dbf(shp_path.with_suffix("").with_suffix(".dbf"), _ID_Factory):
            self._unique_a_ids.append(rec)

    def features(self) -> Generator[Tuple[int, List[SEVASSignRecord]], Any, Any]:
        """
        Returns a generator that reads features from the shapefile grouped by their
        a_id attribute.

        """
        f: SEVASSignRecord
        for a_id in self._unique_a_ids:
            features = []
            for f in load_shp(self._path):
                if f.a_id == a_id:
                    features.append(f)
            yield (a_id, features)
