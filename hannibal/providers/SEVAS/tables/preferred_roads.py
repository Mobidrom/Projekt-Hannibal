from dataclasses import dataclass
from typing import List, Mapping, Tuple

from hannibal.io.shapefile import FeatureLike
from hannibal.providers import HannibalProvider
from hannibal.providers.SEVAS.constants import SEVASDir
from hannibal.providers.SEVAS.tables.base import SEVASBaseRecord, SEVASBaseTable
from hannibal.util.exception import HannibalSchemaError


@dataclass
class SEVASPreferredRoadRecord(SEVASBaseRecord):
    osm_id: int
    fahrtri: SEVASDir
    shape: List[Tuple[float, float]]

    def as_dict(self) -> Mapping[str, str | int]:
        """
        Get the record as a dictionary
        """
        return {"osm_id": self.osm_id, "fahrtri": self.fahrtri.value}

    def tags(self) -> Mapping[str, str]:
        """
        Get the OSM tags for this preferred road segment.
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


class SEVASPreferredRoads(SEVASBaseTable):
    @staticmethod
    def feature_factory(feature: FeatureLike) -> SEVASPreferredRoadRecord:
        """
        The preferred road segment feature factory passed to the shapefile loader
        """
        id_: int = feature["properties"]["osm_id"]
        dir_: SEVASDir = SEVASDir(feature["properties"]["fahrtri"])

        return SEVASPreferredRoadRecord(id_, dir_, feature["geometry"]["coordinates"])

    def invalidating_keys(self) -> Tuple[str]:
        return ("hgv",)
