from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, List, Mapping, Tuple

from hannibal.io.DBF import load_dbf
from hannibal.logging import LOGGER
from hannibal.providers import HannibalProvider
from hannibal.providers.SEVAS.constants import SEVASDir
from hannibal.util.exception import HannibalIOError, HannibalSchemaError
from hannibal.util.immutable import ImmutableMixin


@dataclass
class SEVASPreferredRoadRecord:
    osm_id: int
    fahrtri: SEVASDir

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


def SevasPreferredRoadFactory(items: List[Tuple[str, Any]]) -> SEVASPreferredRoadRecord:
    """
    Factory function passed to the dbf loader to extract all the information we need
    from the preferred road DBF (Dt. Vorrangrouten).

    :return: returns a record
    """
    id_: int | None
    dir_: SEVASDir | None = None
    for k, v in items:
        if k == "fahrtri":
            dir_ = SEVASDir(v)
        elif k == "osm_id":
            id_ = v

    if id_ is not None and dir_ is not None:
        return SEVASPreferredRoadRecord(id_, dir_)

    raise HannibalIOError("Failed to parse preferred road record.")


class SEVASPreferredRoads(ImmutableMixin):
    def __init__(self, dbf_path: Path) -> None:
        """
        SEVAS preferred roads map. The DBF's records are read into memory at initialization by default.

        :param dbf: path to the restriction PBF file.
        """

        self._dbf_path = dbf_path

        # the mapping default value is an empty list
        self._map: Mapping[int, SEVASPreferredRoadRecord] = {}

        # for stats, we keep track of the number of times an OSM ID was accessed
        self._access_count: Mapping[int, int] = {}

        dbf = load_dbf(dbf_path, SevasPreferredRoadFactory)

        record: SEVASPreferredRoadRecord
        for record in dbf.records:
            # handle duplicates: combine if directions are different
            if existing := self._map.get(record.osm_id):
                if int(record.fahrtri.value) + int(existing.fahrtri) == 3:
                    existing.fahrtri = SEVASDir.BOTH
                    LOGGER.warning(
                        f"Combining bi-directional entries in preferred roads: {record.osm_id}"
                    )
                else:
                    LOGGER.warning(
                        f"Duplicate preferred road segment, ignoring additional entry: {record.osm_id}"
                    )
                continue
            self._map[record.osm_id] = record
            self._access_count[record.osm_id] = 0

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
