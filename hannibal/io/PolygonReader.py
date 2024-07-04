from osmium import Area, SimpleHandler
from osmium.geom import WKBFactory
from shapely import Polygon, wkb

from hannibal.logging import LOGGER


class PolygonReader(SimpleHandler):
    def __init__(self, id: int) -> None:
        """
        Helper to retrieve a polygon from an OSM ID. Call the apply_file() method to retrieve a polygon
        from an osm file

        :param id: the OSM ID that identifies an area (could be a relation or a closed way)
        """
        super().__init__()
        self._id = id
        self._geom: Polygon | None = None
        self._name: str | None = None
        self._wkb_fac = WKBFactory()

    def area(self, a: Area):
        if a.orig_id() == self._id:
            if self._geom:
                LOGGER.error(f"More than one area found for id {self._id}")
            shape = self._wkb_fac.create_multipolygon(a)
            self._geom = wkb.loads(shape).geoms[0]
            self._name = a.tags.get("name", None)
            LOGGER.info(f"Relation mit ID gefunden: {self._name}")

    @property
    def geometry(self) -> Polygon | None:
        return self._geom
