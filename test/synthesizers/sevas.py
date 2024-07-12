from pathlib import Path
from typing import List, Mapping

from hannibal.providers.SEVAS.constants import RestrVZ, SEVASLayer
from hannibal.providers.SEVAS.tables.low_emission_zones import SEVAS_LEZ_Record
from hannibal.providers.SEVAS.tables.preferred_roads import SEVASPreferredRoadRecord
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrRecord
from hannibal.providers.SEVAS.tables.road_speeds import SEVASRoadSpeedRecord


class SEVASSynthesizer:
    def __init__(self, base_dir: Path) -> None:
        """
        Class that helps producing fake SEVAS data.

        Performance doesn't really matter so we just use geopandas to easily
        write shapefiles.

        """
        self._base_dir = base_dir

    @staticmethod
    def make_vz(*flags: List[RestrVZ]) -> Mapping[RestrVZ, bool]:
        """
        Creates a Vorzeichen mapping to pass to the SEVAS Restriction Record. Pass the VZ flags you want
        to set to true.
        """
        return {v: True if v in flags else False for v in RestrVZ}

    def write_low_emission_zones(self, features: List[SEVAS_LEZ_Record]):
        """
        Write low emission zone polygons to a shapefile.
        """
        if not len(features):
            raise ValueError("Feature list cannot be empty")

        try:
            import geopandas as gpd
        except ImportError:
            raise ImportError("Geopandas must be installed to run the test data creation.")

        df = gpd.GeoDataFrame.from_features(features, crs="epsg:4326")
        path = self._base_dir / SEVASLayer.LOW_EMISSION_ZONES.value
        df.to_file(path.with_suffix(".shp"))

    def write_segment_features(
        self,
        features: List[SEVASRestrRecord] | List[SEVASRoadSpeedRecord] | List[SEVASPreferredRoadRecord],
    ):
        """
        Write segment features (i.e. restrictions, preferred roads and road speeds) to DBF file.
        Expects a list of features of the same type.
        """
        if not len(features):
            raise ValueError("Feature list cannot be empty")

        layer: str

        # assume the caller is not mixing types here
        if isinstance(features[0], SEVASRestrRecord):
            layer = SEVASLayer.RESTRICTIONS.value
        elif isinstance(features[0], SEVASRoadSpeedRecord):
            layer = SEVASLayer.ROAD_SPEEDS.value
        elif isinstance(features[0], SEVASPreferredRoadRecord):
            layer = SEVASLayer.PREFERRED_ROADS.value
        else:
            raise ValueError(
                "The segment synthesizer only accepts restrictions, preferred road segments and road "
                "speed segment type features."
            )

        try:
            import geopandas as gpd
        except ImportError:
            raise ImportError("Geopandas must be installed to run the test data creation.")

        df = gpd.GeoDataFrame.from_features(features).set_crs("epsg:4326")
        path = self._base_dir / layer
        gpd.GeoDataFrame(df).to_file(path.with_suffix(".shp"))
