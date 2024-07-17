from pathlib import Path
from typing import Tuple

import pytest
from shapely import LineString

from hannibal.providers.SEVAS.constants import RestrVZ, SEVASDir, SEVASRestrType
from hannibal.providers.SEVAS.provider import SEVASProvider
from test.integration.SEVAS import get_provider_args
from test.make_data import make_osm_test_data, restriction_factory
from test.synthesizers.osm import OSMSynthesizer
from test.synthesizers.sevas import SEVASSynthesizer
from test.util.geo import line_in_list
from test.util.osm import OSMTestHandler


@pytest.fixture(name="converted_restrictions")
def make_restriction_data():
    name = "restriction_test"

    ascii_map = """
A---B---C---D---E---F
|                   |
|                   |
|       J---I---H---G
|       |
|       |
W---N---M---K--L----O
    |   |           |
    |   |           |
    V---S----R------P
"""

    ways = {
        "AB": (0, {"highway": "tertiary", "maxlength": "10"}),
        "BC": (1, {"highway": "tertiary"}),
        "CD": (2, {"highway": "tertiary"}),
        "DE": (3, {"highway": "tertiary"}),
        "EF": (4, {"highway": "tertiary", "maxweight": "3.5"}),
        "FG": (5, {"highway": "tertiary", "maxweight:hgv": "5"}),
        "GH": (6, {"highway": "tertiary", "maxwidth": "6", "hazard": "no"}),
        "HI": (7, {"highway": "tertiary", "maxlength": "1", "hgv": "no"}),
        "IJ": (8, {"highway": "tertiary"}),
        "JM": (9, {"highway": "tertiary"}),
        "MK": (10, {"highway": "tertiary"}),
        "KL": (11, {"highway": "tertiary"}),
        "LO": (12, {"highway": "tertiary"}),
        "OP": (13, {"highway": "tertiary"}),
        "PR": (14, {"highway": "tertiary"}),
        "RS": (15, {"highway": "tertiary"}),
        "SV": (16, {"highway": "tertiary"}),
        "SM": (17, {"highway": "tertiary"}),
        "MN": (18, {"highway": "tertiary"}),
        "VN": (19, {"highway": "tertiary"}),
        "NW": (20, {"highway": "tertiary"}),
        "WA": (21, {"highway": "tertiary"}),
    }
    osm, path = make_osm_test_data(ascii_map, name, ways=ways)
    restrictions = [
        restriction_factory(
            0,
            SEVASDir.BOTH,
            SEVASRestrType.HEIGHT,
            "7,5",
            shape=osm.way_coordinates("AB"),
            vz=[RestrVZ.VZ_1020_30],
        ),
        restriction_factory(
            1,
            SEVASDir.FORW,
            SEVASRestrType.AXLE_LOAD,
            "1",
            shape=osm.way_coordinates("BC"),
        ),
        restriction_factory(
            2,
            SEVASDir.BACKW,
            SEVASRestrType.HGV_NO,
            "",
            shape=osm.way_coordinates("CD"),
        ),
        restriction_factory(
            2,
            SEVASDir.FORW,
            SEVASRestrType.WEIGHT,
            "3,6",
            shape=osm.way_coordinates("CD"),
        ),
    ]
    sevas = SEVASSynthesizer(path)
    sevas.write_segment_features(restrictions)

    args = get_provider_args(path)
    provider = SEVASProvider(**args)
    provider.process()

    counter = OSMTestHandler()
    counter.apply_file(args["out_path"], locations=True)

    yield counter, osm

    for file in path.glob("*"):
        file.unlink()

    path.rmdir()


def test_object_count(converted_restrictions):
    counter, _ = converted_restrictions
    assert counter.way_count == 22
    assert counter.node_count == 20
    assert counter.relation_count == 0


@pytest.mark.parametrize(
    ["way_name", "count"],
    [
        ("AB", 1),
        ("BC", 1),
        ("CD", 1),
        ("DE", 1),
        ("EF", 1),
    ],
)
def test_shape_count(converted_restrictions, way_name: str, count: int):
    counter, _ = converted_restrictions
    assert len(counter.way_shapes[way_name]) == count


@pytest.mark.parametrize(
    ["way_coordinates", "way_name"],
    [
        ("AB", "AB"),
        ("DE", "DE"),
    ],
)
def test_shapes(converted_restrictions, way_coordinates: str, way_name: str):
    counter, osm = converted_restrictions
    line_in_list(LineString(osm.way_coordinates(way_coordinates)), counter.way_shapes[way_name])


@pytest.mark.parametrize(
    ["tag_combination", "count"],
    [
        (("way", "highway", "tertiary"), 22),
        (("way", "maxweight", "3.5"), 1),
        (("way", "hgv:backward", "no"), 1),
        (("way", "maxweight:forward", "3.6"), 1),
        (("way", "maxweight:hgv", "5"), 1),
        (("way", "maxheight", "7.5"), 1),
        (("way", "maxheight:conditional", "none @ destination"), 1),
        (("way", "traffic_sign", "DE:265,1020-30"), 1),
    ],
)
def test_tag_counts(
    converted_restrictions: Tuple[OSMSynthesizer, Path],
    tag_combination: Tuple[str, str, str],
    count: int,
):
    counter, _ = converted_restrictions
    assert (
        r := counter.counter[tag_combination]
    ) == count, f"Tag count incorrect for {tag_combination}, expected {count}, found {r}"
