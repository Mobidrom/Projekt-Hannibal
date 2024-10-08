from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from rich import print

from hannibal.config.HannibalConfig import TagCleanConfig
from hannibal.io.OSM import OSMRewriter
from hannibal.logging import LOGGER
from hannibal.providers.SEVAS.client import SEVASClient
from hannibal.providers.SEVAS.constants import SEVASLayer
from hannibal.providers.SEVAS.tables.low_emission_zones import SEVAS_LEZ
from hannibal.providers.SEVAS.tables.preferred_roads import SEVASPreferredRoads
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions
from hannibal.providers.SEVAS.tables.road_speeds import SEVASRoadSpeeds
from hannibal.stats.stats import StatsCategory

# should be fine for another couple of years
# just increment in case of ID collisions
START_OBJ_ID = 2**45 - 1


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
        tag_clean_config: TagCleanConfig | None = None,
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
        :param tag_clean_config: optionally, a config can be parsed that contains information on which
            tags to remove on objects inside given polygons
        """

        self._in_path = in_path
        self._out_path = out_path

        # download data
        if download_data:
            self._client = SEVASClient(data_path, base_url)
            self._client.get_all()

        self._polygons_path = data_path / (SEVASLayer.LOW_EMISSION_ZONES.value + ".shp")
        self._polygons_segments_path = data_path / (SEVASLayer.ROAD_SPEEDS.value + ".shp")
        self._restrictions_path = data_path / (SEVASLayer.RESTRICTIONS.value + ".shp")
        self._preferred_roads_path = data_path / (SEVASLayer.PREFERRED_ROADS.value + ".shp")
        self._signs_path = data_path / (SEVASLayer.TRAFFIC_SIGNS.value + ".shp")

        # create mappings OSM_ID -> sevas_records
        # to overwrite tags of existing objects

        # these can be none, if the respective file could not be found
        restrictions, preferred_roads, road_speeds, low_emission_zones = None, None, None, None
        if self._restrictions_path.exists():
            LOGGER.info("Found restrictions.")
            restrictions = SEVASRestrictions(self._restrictions_path)

        if self._preferred_roads_path.exists():
            LOGGER.info("Found preferred road segments.")
            preferred_roads = SEVASPreferredRoads(self._preferred_roads_path)

        if self._polygons_segments_path.exists():
            LOGGER.info("Found road speed segments.")
            road_speeds = SEVASRoadSpeeds(self._polygons_segments_path)

        if self._polygons_path.exists():
            LOGGER.info("Found low emission zones.")
            # read shapefiles from which new objects will be created
            low_emission_zones = SEVAS_LEZ(self._polygons_path)

        # traffic_signs = SEVASTrafficSigns

        self._rewriter: OSMRewriter = OSMRewriter(
            in_path,
            out_path,
            start_node_id,
            start_way_id,
            start_rel_id,
            restrictions,
            preferred_roads,
            road_speeds,
            low_emission_zones,
            tag_clean_config,
        )

    def process(self):
        """
        Starts the actual conversion process by applying the base OSM file to the rewriter
        """
        LOGGER.info(f"Processing OSM file: {self._in_path}")
        self._rewriter.apply_file(self._in_path, locations=True)

        # write any new geometries (low emission zones, traffic signs)
        next_node_id = self._rewriter.write_low_emission_zones()
        self._next_node_id = next_node_id

        self._rewriter.close()
        self._rewriter.merge()
        print(f"SEVAS Konvertierung abgeschlossen. Finale OSM Datei: [bold]{self._out_path}[/bold]")

    def report(self):
        print("")
        print("[bold][blue]#__________ Report __________#[/blue][/bold]")
        print("")
        print("Anzahl hinzugefügter Tags pro Layer")
        added = dict(self._rewriter._reporter[StatsCategory.ADDED.value])
        print(f"\t{added}")
        print("Anzahl durch SEVAS invalidierter Tags pro Layer")
        overridden = dict(self._rewriter._reporter[StatsCategory.OVERRIDDEN.value])
        print(f"\t{overridden}")
        if self._rewriter._tag_clean_config:
            print(f"Anzahl in relation {self._rewriter._tag_clean_config.id} entfernter Tags")
            cleaned = dict(self._rewriter._reporter[StatsCategory.REMOVED.value])
            print(f"\t{cleaned}")

    def unmatched_features(self) -> Dict[str, List[int]]:
        feats = defaultdict(list)
        for layer in self._rewriter._get_available_way_layers():
            for feature in layer.unmatched_features():
                feats[layer.layer_name].append(feature.segment_id)

        return feats
