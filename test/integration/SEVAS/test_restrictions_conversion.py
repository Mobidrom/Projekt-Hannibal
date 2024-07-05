from pathlib import Path
from typing import Mapping, Tuple

import pytest

from hannibal.providers.SEVAS.provider import SEVASProvider
from test import BASE_DATA_DIR
from test.util.osm import TagCounter


def get_provider_args(base_dir: Path) -> Mapping[str, str]:
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


@pytest.mark.parametrize(
    ["directory", "tag_counts"],
    [
        (
            "restriction_test",
            {
                ("way", "highway", "tertiary"): 22,
                ("way", "maxweight", "3.5"): 1,
                ("way", "maxweight:hgv", "5"): 1,
                ("way", "maxheight", "7.5"): 1,
                ("way", "maxheight:conditional", "none @ destination"): 1,
                ("way", "traffic_sign", "DE:265,1020-30"): 1,
            },
        )
    ],
)
def test_object_count(directory: str, tag_counts: Mapping[Tuple[str, str, str], int]):
    path = BASE_DATA_DIR / directory
    provider_args = get_provider_args(path)
    provider = SEVASProvider(**provider_args)
    provider.process()

    counter = TagCounter(tag_counts)
    counter.apply_file(provider_args["out_path"])
    print(counter.counter)
    for t, ec in tag_counts.items():
        assert (r := counter.counter[t]) == ec, f"Tag count incorrect for {t}, expected {ec}, found {r}"
