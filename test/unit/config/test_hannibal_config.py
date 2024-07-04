from pathlib import Path
from typing import Callable

import pytest

from hannibal.config.HannibalConfig import (
    HannibalConfig,
    OsmBaseConfig,
    OutputConfig,
    ProviderBaseConfig,
)
from hannibal.providers import HannibalProvider

YML_PATH = Path("test/data/test_config.yml")


@pytest.fixture()
def make_config():
    def write_config(s: str):
        with open(YML_PATH, "w") as fh:
            fh.write(s)

    yield write_config
    YML_PATH.unlink()


@pytest.mark.parametrize(
    ["raw_yml", "expected_config"],
    [
        (
            """
providers:
    sevas:
        clean_tags:
          active: true
          tags:
            - maxspeed
          area: 123
osm_base:
    path: "some_path"
    url: "https://endless.horse"
output:
  path: "output.pbf"
""",
            HannibalConfig(
                providers={HannibalProvider.SEVAS: ProviderBaseConfig(True, ["maxspeed"], 123)},
                osm_base=OsmBaseConfig(Path("some_path"), "https://endless.horse"),
                output=OutputConfig(Path("output.pbf")),
            ),
        )
    ],
)
def test_config(make_config: Callable, raw_yml: str, expected_config: HannibalConfig):
    make_config(raw_yml)
    config = HannibalConfig.from_path(YML_PATH)

    assert config == expected_config
