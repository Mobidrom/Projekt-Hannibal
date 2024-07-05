import pytest

from hannibal.providers.SEVAS.constants import CommonRestrSignatures
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions
from test.unit.providers.SEVAS.constants import (
    RESTRICTION_PATH,
    TEST_RESTRICTIONS,
)

TEST_HAS_TIME = {4003447: False, 16941331: True, 494470560: False, 415352315: False, 135810076: False}

TEST_RESTRICTION_TAGS = {
    4003447: {"hgv": "destination", "traffic_sign": "DE:253,1020-30"},
    135810076: {"maxheight": "3.1", "traffic_sign": "DE:265"},
    415352315: {"maxlength": "10", "traffic_sign": "DE:266"},
    176232057: {"hazmat": "no", "traffic_sign": "DE:261"},
    690337668: {
        "maxweight": "3.5",
        "maxweight:conditional": "none @ delivery",
        "traffic_sign": "DE:262,1026-35",
    },
    132408287: {"hgv": "delivery", "traffic_sign": "DE:253,1026-35"},
    171772366: {
        "maxweight:forward": "7.5",
        "maxweight:forward:conditional": "none @ delivery",
        "traffic_sign": "DE:253,1026-35,1053-33",
    },
    52350372: {"hgv:conditional": "no @ 06:00-22:00;yes @ delivery", "traffic_sign": "DE:253,1026-35"},
    762953386: {"maxweight:conditional": "4 @ 17:00-08:00", "traffic_sign": "DE:262"},
}

TEST_SIGNATURES = {
    16941331: "262" + "0" * 23,
    494470560: "25300010000000000000000000",
    4218825: "25300000000000100000000100",
    4003447: CommonRestrSignatures.HGV_NO_DEST_ONLY.value,
}


@pytest.fixture
def sevas_restrictions():
    return SEVASRestrictions(RESTRICTION_PATH)


def test_number_of_restrictions(sevas_restrictions: SEVASRestrictions):
    """
    Gets a Restriction table object and tests the number of total restrictions in there.
    """
    assert sum([len(way) for _, way in sevas_restrictions.items()]) == 1337
    assert sum([len(way) for way in sevas_restrictions.values()]) == 1337


@pytest.mark.parametrize("osm_id,expected_count", [(272345750, 2), (375986802, 1), (132630677, 2)])
def test_osm_id_mapping(sevas_restrictions: SEVASRestrictions, osm_id, expected_count):
    """
    Checks that the mapping of OSM-ID --> List[Restrictions] works as expected
    """
    restrs = sevas_restrictions[osm_id]

    assert len(restrs) == expected_count

    for r in restrs:
        assert r.osm_id == osm_id


@pytest.mark.parametrize("osm_id", TEST_RESTRICTIONS.keys())
def test_restriction_fields(sevas_restrictions: SEVASRestrictions, osm_id):
    """
    Checks whether the fields of a given restriction object created from the DBF are set as expected
    """
    assert len(sevas_restrictions[osm_id]) == 1
    restr = sevas_restrictions[osm_id][0]

    expected = TEST_RESTRICTIONS[osm_id]

    assert restr.segment_id == expected.segment_id
    assert restr.restrkn_id == expected.restrkn_id
    assert restr.name == expected.name
    assert restr.osm_vers == expected.osm_vers
    assert restr.osm_id == expected.osm_id
    assert restr.fahrtri == expected.fahrtri
    assert restr.typ == expected.typ
    assert restr.wert == expected.wert
    assert restr.tage_einzl == expected.tage_einzl
    assert restr.tage_grppe == expected.tage_grppe
    assert restr.zeit1_von == expected.zeit1_von
    assert restr.zeit1_bis == expected.zeit1_bis
    assert restr.zeit2_von == expected.zeit2_von
    assert restr.zeit2_bis == expected.zeit2_bis
    assert restr.gemeinde == expected.gemeinde
    assert restr.kreis == expected.kreis
    assert restr.regbezirk == expected.regbezirk

    # check the additional sign boolean flags
    for k, v in expected.vz.items():
        assert restr.vz[k] == v


@pytest.mark.parametrize("osm_id", TEST_SIGNATURES.keys())
def test_signatures(sevas_restrictions: SEVASRestrictions, osm_id):
    """
    Checks whether the restriction signatures match up with the expected signatures.
    """

    restr = sevas_restrictions[osm_id][0]

    assert restr.sign_signature() == TEST_SIGNATURES[osm_id]


@pytest.mark.parametrize("osm_id", TEST_RESTRICTION_TAGS.keys())
def test_simple_tags(sevas_restrictions: SEVASRestrictions, osm_id):
    """
    Checks whether a restriction's tags match up with the expected tags.
    """

    restr = sevas_restrictions[osm_id][0]

    expected_tags = TEST_RESTRICTION_TAGS[osm_id]
    tags = restr.tags()

    assert len(tags) == len(expected_tags)

    for k, v in tags.items():
        ev = expected_tags[k]

        assert v == ev


@pytest.mark.parametrize("osm_id", TEST_HAS_TIME.keys())
def test_has_time(sevas_restrictions: SEVASRestrictions, osm_id):
    """
    Make sure we recognize the presence of time cases correctly
    """

    restr = sevas_restrictions[osm_id][0]

    assert restr.has_time_case() == TEST_HAS_TIME[osm_id]
