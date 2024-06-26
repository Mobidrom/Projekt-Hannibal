from pathlib import Path

from rich import print

from hannibal.io.OSM import OSMRewriter
from hannibal.logging import LOGGER
from hannibal.providers.SEVAS.client import SEVASClient
from hannibal.providers.SEVAS.constants import SEVASLayer
from hannibal.providers.SEVAS.tables.low_emission_zones import SEVAS_LEZ
from hannibal.providers.SEVAS.tables.preferred_roads import SEVASPreferredRoads
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions
from hannibal.providers.SEVAS.tables.road_speeds import SEVASRoadSpeeds

START_OBJ_ID = 2**55 - 1


class SEVASProvider:
    def __init__(
        self,
        in_path: Path,
        out_path: Path,
        base_url: str,
        data_path: Path,
        download_data: bool = True,
        start_node_id: int = START_OBJ_ID,
        start_way_id: int = START_OBJ_ID,
        start_rel_id: int = START_OBJ_ID,
    ) -> None:
        """
        Provider class that handles the SEVAS conversion.

        :param in_path: Path to base OSM file. Contents will not be altered.
        :param out_path: Path to the resulting OSM file. Contains contents from base OSM file,
                         with changes based on SEVAS data.
        :param data_path: Path to directory where SEVAS data will be stored.
        :param baseurl: Base URL that points to the SEVAS Web Feature Service
        :param download_data: whether or not to download SEVAS data
        :param max_node_id: the integer value from which new node IDs will be created incrementally
        :param max_way_id: the integer value from which new way IDs will be created incrementally
        :param max_rel_id: the integer value from which new relation IDs will be created incrementally
        """

        self._in_path = in_path
        self._out_path = out_path

        self._next_node_id = start_node_id
        self._next_way_id = start_way_id
        self._next_rel_id = start_rel_id

        # download data
        if download_data:
            self._client = SEVASClient(data_path, base_url)
            self._client.get_all()

        self._polygons_path = data_path / (SEVASLayer.LOW_EMISSION_ZONES.value + ".shp")
        self._polygons_segments_path = data_path / (SEVASLayer.ROAD_SPEEDS.value + ".dbf")
        self._restrictions_path = data_path / (SEVASLayer.RESTRICTIONS.value + ".dbf")
        self._preferred_roads_path = data_path / (SEVASLayer.PREFERRED_ROADS.value + ".dbf")
        self._signs_path = data_path / (SEVASLayer.TRAFFIC_SIGNS.value + ".dbf")

        # create mappings OSM_ID -> sevas_records
        # to overwrite tags of existing objects
        restrictions = SEVASRestrictions(self._restrictions_path)
        preferred_roads = SEVASPreferredRoads(self._preferred_roads_path)
        road_speeds = SEVASRoadSpeeds(self._polygons_segments_path)

        # read shapefiles from which new objects will be created
        low_emission_zones = SEVAS_LEZ(self._polygons_path)
        # traffic_signs = SEVASTrafficSigns

        self._rewriter: OSMRewriter = OSMRewriter(
            in_path, out_path, restrictions, preferred_roads, road_speeds, low_emission_zones
        )

    def process(self):
        """
        Starts the actual conversion process by applying the base OSM file to the rewriter
        """
        LOGGER.info(f"Processing OSM file: {self._in_path}")
        self._rewriter.apply_file(self._in_path)

        # write any new geometries (low emission zones, traffic signs)
        next_node_id = self._rewriter.write_low_emission_zones(
            self._next_node_id, self._next_way_id, self._next_rel_id
        )
        self._next_node_id = next_node_id

        self._rewriter.close()
        self._rewriter.merge()

    def report(self):
        print(self._rewriter._reporter)
