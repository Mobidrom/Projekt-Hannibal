from typing import Dict

import pytest

from hannibal.providers.SEVAS.tables.road_speeds import (
    SEVASRoadSpeedRecord,
    SEVASRoadSpeeds,
    SEVASRoadSpeedType,
)
from test.make_data import road_speed_factory
from test.unit.providers.SEVAS.constants import (
    POLYGON_SEGMENTS_PATH,
)

ORDERED_SPEED_TYPES = [
    SEVASRoadSpeedType.PEDESTRIAN,
    SEVASRoadSpeedType.CALM_TRAFFIC,
    SEVASRoadSpeedType.S20,
    SEVASRoadSpeedType.S30,
    SEVASRoadSpeedType.URBAN,
]

# these tests are on real-world SEVAS data
TEST_ROAD_SPEED_TAGS = {
    255602524: {
        "maxspeed": "30",
        "zone:traffic": "DE:zone30",
        "maxspeed:type": "DE:zone30",
        "source:maxspeed": "DE:zone30",
    },
    23198836: {
        "maxspeed": "30",
        "zone:traffic": "DE:zone30",
        "maxspeed:type": "DE:zone30",
        "source:maxspeed": "DE:zone30",
    },
}

TEST_ROAD_SPEEDS = {
    23198836: SEVASRoadSpeedRecord(
        4109996,
        4101,
        "Peter-Berchem-Straße",
        "osm_20240404",
        23198836,
        "tempozone",
        "274.1",
        "Köln",
        "Köln",
        "Köln",
        [(0, 0), (1, 1)],
    )
}


@pytest.fixture()
def sevas_road_speeds():
    return SEVASRoadSpeeds(POLYGON_SEGMENTS_PATH)


def test_number_of_road_speeds(sevas_road_speeds: SEVASRoadSpeeds):
    """
    Gets a Restriction table object and tests the number of total road speeds in there.
    """
    assert len([p for p in sevas_road_speeds.items()]) == 11091
    assert len([p for p in sevas_road_speeds.values()]) == 11091


@pytest.mark.parametrize("osm_id", TEST_ROAD_SPEEDS.keys())
def test_road_speed_fields(sevas_road_speeds: SEVASRoadSpeeds, osm_id: int):
    """
    Checks whether the fields of a given restriction object created from the DBF are set as expected
    """
    restr = sevas_road_speeds[osm_id][0]
    expected = TEST_ROAD_SPEEDS[osm_id]

    assert restr.osm_id == expected.osm_id
    assert restr.typ == expected.typ
    assert restr.wert == expected.wert
    assert restr.name == expected.name
    assert restr.gemeinde == expected.gemeinde
    assert restr.kreis == expected.kreis
    assert restr.regbezirk == expected.regbezirk


@pytest.mark.parametrize("osm_id", TEST_ROAD_SPEED_TAGS.keys())
def test_simple_tags(sevas_road_speeds: SEVASRoadSpeeds, osm_id):
    """
    Checks whether a road speed's tags match up with the expected tags.
    """

    restrs = sevas_road_speeds[osm_id]
    assert len(restrs) == 1
    restr = restrs[0]

    tags = restr.tags()

    for k, v in tags.items():
        print(f"{k}: {v}")
        assert v == TEST_ROAD_SPEED_TAGS[osm_id][k]


# from here on, tests are run on fake SEVAS data created on the fly
@pytest.mark.parametrize(
    ["record", "tags"],
    [
        (
            road_speed_factory(0, SEVASRoadSpeedType.S30),
            {
                "maxspeed": "30",
                "maxspeed:type": "DE:zone30",
                "zone:traffic": "DE:zone30",
                "source:maxspeed": "DE:zone30",
            },
        ),
    ],
)
def test_record_tags(record: SEVASRoadSpeedRecord, tags: Dict[str, str]):
    assert record.tags() == tags


@pytest.mark.parametrize(
    ["one", "other"],
    [(one, other) for one in ORDERED_SPEED_TYPES for other in ORDERED_SPEED_TYPES if one != other],
)
def test_road_speed_sorting_greater_than(one: SEVASRoadSpeedType, other: SEVASRoadSpeedType):
    assert (one > other) == (ORDERED_SPEED_TYPES.index(one) > ORDERED_SPEED_TYPES.index(other))


@pytest.mark.parametrize(
    ["one", "other"],
    [(one, other) for one in ORDERED_SPEED_TYPES for other in ORDERED_SPEED_TYPES if one != other],
)
def test_road_speed_sorting_less_than(one: SEVASRoadSpeedType, other: SEVASRoadSpeedType):
    assert (one < other) == (ORDERED_SPEED_TYPES.index(one) < ORDERED_SPEED_TYPES.index(other))
