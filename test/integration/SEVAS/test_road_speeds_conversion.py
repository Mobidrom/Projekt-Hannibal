from pathlib import Path
from typing import Tuple

import pytest
from shapely import LineString

from hannibal.providers.SEVAS.provider import SEVASProvider
from hannibal.providers.SEVAS.tables.road_speeds import SEVASRoadSpeedType
from test.integration.SEVAS import get_provider_args
from test.make_data import make_osm_test_data, road_speed_factory
from test.synthesizers.osm import OSMSynthesizer
from test.synthesizers.sevas import SEVASSynthesizer
from test.util.geo import line_in_list
from test.util.osm import OSMTestHandler


@pytest.fixture(name="converted_road_speeds")
def road_speed_setup():
    name = "split_road_speeds"
    ascii_map = """
A---1--------B-2-----C-3---4--D-----E----F
"""
    gridsize = 100
    ways = {
        "AB": (0, {"highway": "residential"}),
        "BC": (1, {"highway": "residential"}),
        "CD": (2, {"highway": "residential"}),
        "DE": (3, {"highway": "residential"}),
        "EF": (4, {"highway": "residential"}),
    }
    osm, path = make_osm_test_data(ascii_map, name, ways=ways, grid_size=gridsize)
    road_speeds = [
        road_speed_factory(0, SEVASRoadSpeedType.S30, osm.way_coordinates("A1")),
        road_speed_factory(1, SEVASRoadSpeedType.S30, osm.way_coordinates("2C")),
        road_speed_factory(2, SEVASRoadSpeedType.S30, osm.way_coordinates("34")),
        road_speed_factory(3, SEVASRoadSpeedType.S30, osm.way_coordinates("DE")),
        # make sure the strictest one applies
        road_speed_factory(4, SEVASRoadSpeedType.S30, osm.way_coordinates("EF")),
        road_speed_factory(4, SEVASRoadSpeedType.URBAN, osm.way_coordinates("EF")),
        road_speed_factory(4, SEVASRoadSpeedType.S20, osm.way_coordinates("EF")),
    ]
    sevas = SEVASSynthesizer(path)
    sevas.write_segment_features(road_speeds)

    args = get_provider_args(path)
    provider = SEVASProvider(**args)
    provider.process()

    counter = OSMTestHandler()
    counter.apply_file(args["out_path"], locations=True)

    yield counter, osm

    for file in path.glob("*"):
        file.unlink()

    path.rmdir()


def test_object_count(converted_road_speeds):
    counter, _ = converted_road_speeds
    assert counter.way_count == 9
    assert counter.node_count == 14
    assert counter.relation_count == 0


@pytest.mark.parametrize(
    ["way_name", "count"],
    [
        ("AB", 2),
        ("BC", 2),
        ("CD", 3),
        ("DE", 1),
        ("EF", 1),
    ],
)
def test_shape_count(converted_road_speeds, way_name: str, count: int):
    counter, _ = converted_road_speeds
    assert len(counter.way_shapes[way_name]) == count


@pytest.mark.parametrize(
    ["way_coordinates", "way_name"],
    [
        ("A1", "AB"),
        ("1B", "AB"),
        ("B2", "BC"),
        ("2C", "BC"),
        ("C3", "CD"),
        ("34", "CD"),
        ("4D", "CD"),
        ("DE", "DE"),
    ],
)
def test_shapes(converted_road_speeds, way_coordinates: str, way_name: str):
    counter, osm = converted_road_speeds
    line_in_list(LineString(osm.way_coordinates(way_coordinates)), counter.way_shapes[way_name])


@pytest.mark.parametrize(
    ["tag_combination", "count"],
    [
        (("way", "maxspeed", "30"), 4),
        (("way", "zone:traffic", "DE:zone30"), 4),
        (("way", "source:maxspeed", "DE:zone30"), 4),
        (("way", "maxspeed:type", "DE:zone30"), 4),
        (("way", "maxspeed", "20"), 1),
    ],
)
def test_tag_counts(
    converted_road_speeds: Tuple[OSMSynthesizer, Path],
    tag_combination: Tuple[str, str, str],
    count: int,
):
    counter, _ = converted_road_speeds
    assert (
        r := counter.counter[tag_combination]
    ) == count, f"Tag count incorrect for {tag_combination}, expected {count}, found {r}"
