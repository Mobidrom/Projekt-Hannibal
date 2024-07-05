import pytest

from hannibal.providers.SEVAS.tables.low_emission_zones import SEVAS_LEZ
from test.unit.providers.SEVAS.constants import LEZ_PATH

TEST_LEZ = {3191: {"shape_length": 170, "wert": "1031-52", "typ": "umweltzone"}}
TEST_LOW_EMISSION_TAGS = {3191: {"type": "boundary", "boundary": "low_emission_zone"}}


@pytest.fixture
def sevas_lez():
    return SEVAS_LEZ(LEZ_PATH)


def test_number_of_lez(sevas_lez: SEVAS_LEZ):
    """
    Gets a Restriction table object and tests the number of total low emission zones in there.
    """
    assert len([p for p in sevas_lez.features()]) == 10
    assert len([p for p in sevas_lez.features()]) == 10


@pytest.mark.parametrize("zone_id", TEST_LEZ.keys())
def test_lez_fields(sevas_lez: SEVAS_LEZ, zone_id):
    """
    Checks whether the fields of a given low emission zone object created from
    the shp are set as expected
    """
    lezs = [f for f in sevas_lez.features() if f.zone_id == zone_id]

    assert len(lezs) == 1
    lez = lezs[0]
    expected = TEST_LEZ[zone_id]

    assert lez.typ.value == expected["typ"]
    assert lez.wert.value == expected["wert"]
    assert len(lez.shape[0]) == expected["shape_length"]


@pytest.mark.parametrize("zone_id", TEST_LOW_EMISSION_TAGS.keys())
def test_simple_tags(sevas_lez: SEVAS_LEZ, zone_id: int):
    """
    Checks whether a restriction's tags match up with the expected tags.
    """

    lez = [f for f in sevas_lez.features() if f.zone_id == zone_id][0]

    for k, v in lez.tags().items():
        assert v == TEST_LOW_EMISSION_TAGS[zone_id][k]
