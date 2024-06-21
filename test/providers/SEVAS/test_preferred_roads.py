import pytest

from hannibal.providers.SEVAS.tables.preferred_roads import SEVASPreferredRoadRecord, SEVASPreferredRoads
from test.providers.SEVAS.constants import (
    PREFERRED_ROADS_PATH,
)

TEST_PREFERRED_ROAD_TAGS = {
    2829323: {"hgv": "designated"},
    329035704: {"hgv:forward": "designated"},
}

TEST_PREFERRED_ROADS = {2829323: SEVASPreferredRoadRecord(2829323, "0")}


@pytest.fixture
def sevas_preferred_roads():
    return SEVASPreferredRoads(PREFERRED_ROADS_PATH)


def test_number_of_preferred_roads(sevas_preferred_roads: SEVASPreferredRoads):
    """
    Gets a Restriction table object and tests the number of total preferred roads in there.
    """
    # accounting for duplicates
    assert len([p for p in sevas_preferred_roads.items()]) == 2330
    assert len([p for p in sevas_preferred_roads.values()]) == 2330


@pytest.mark.parametrize("osm_id", TEST_PREFERRED_ROADS.keys())
def test_restriction_fields(sevas_preferred_roads: SEVASPreferredRoads, osm_id):
    """
    Checks whether the fields of a given restriction object created from the DBF are set as expected
    """
    restr = sevas_preferred_roads[osm_id]

    expected = TEST_PREFERRED_ROADS[osm_id]

    assert restr.osm_id == expected.osm_id
    assert restr.fahrtri == expected.fahrtri


@pytest.mark.parametrize("osm_id", TEST_PREFERRED_ROAD_TAGS.keys())
def test_simple_tags(sevas_preferred_roads: SEVASPreferredRoads, osm_id):
    """
    Checks whether a restriction's tags match up with the expected tags.
    """

    restr = sevas_preferred_roads[osm_id]

    tag = restr.tag()

    assert len(tag) == len(TEST_PREFERRED_ROAD_TAGS[osm_id])

    for k, v in tag.items():
        assert v == TEST_PREFERRED_ROAD_TAGS[osm_id][k]
