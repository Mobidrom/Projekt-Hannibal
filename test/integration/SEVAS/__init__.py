from pathlib import Path
from typing import Dict


def get_provider_args(base_dir: Path) -> Dict[str, str]:
    """
    The fake test data sets all adhere to the same directory structure:
      1. map.pbf is the OSM data set
      2. all the SEVAS data is saved as <layer_name>.<ext>, just like the real data
      3. conversion.pbf will be the output
    """

    return {
        "in_path": base_dir / "map.pbf",
        "out_path": base_dir / "conversion.pbf",
        "base_url": "https://sevas.nrw.de/osm/sevas",
        "data_path": base_dir,
        "download_data": False,
    }
