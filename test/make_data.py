from typing import List, Tuple

from hannibal.providers.SEVAS.constants import (
    NO_TAGE_EINZL,
    RestrVZ,
    SEVASDir,
    SEVASRestrType,
    SEVASZoneType,
)
from hannibal.providers.SEVAS.tables.low_emission_zones import SEVAS_LEZ_Record, SEVASLEZType
from hannibal.providers.SEVAS.tables.preferred_roads import SEVASPreferredRoadRecord
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrRecord
from hannibal.providers.SEVAS.tables.road_speeds import SEVASRoadSpeedRecord, SEVASRoadSpeedType
from test import BASE_DATA_DIR
from test.synthesizers.osm import MemberRole, MemberType, OSMSynthesizer, SynthMember, SynthRelation
from test.synthesizers.sevas import SEVASSynthesizer


def restriction_factory(
    segment_id: int,
    restrkn_id: int,
    osm_id: int,
    fahrtri: SEVASDir,
    typ: SEVASRestrType,
    wert: str,
    tage_einzl: str = NO_TAGE_EINZL,
    tage_grppe: str = "0",
    zeit1_von: str = "",
    zeit1_bis: str = "",
    zeit2_von: str = "",
    zeit2_bis: str = "",
    shape: List[Tuple[float, float]] = [],
    vz: List[RestrVZ] = [],
) -> SEVASRestrRecord:
    return SEVASRestrRecord(
        segment_id,
        restrkn_id,
        "test",
        osm_id,
        "version",
        fahrtri,
        typ,
        wert,
        tage_einzl,
        tage_grppe,
        zeit1_von,
        zeit1_bis,
        zeit2_von,
        zeit2_bis,
        "test",
        "test",
        "test",
        shape=shape,
        vz=SEVASSynthesizer.make_vz(*vz),
    )


def road_speed_factory(
    osm_id: int,
    wert: SEVASRoadSpeedType,
    shape: List[Tuple[float, float]] = [],
):
    return SEVASRoadSpeedRecord(
        segment_id=0,
        zone_id=0,
        name="blah",
        osm_vers="0",
        osm_id=osm_id,
        typ=SEVASZoneType.SPEED,
        wert=wert,
        gemeinde="Köln",
        kreis="Köln",
        regbezirk="Köln",
        shape=shape,
    )


def low_emission_zone_factory(
    zone_id: int,
    wert: SEVASLEZType,
    shape: List[List[List[int]]],
    gemeinde: str = "Köln",
    kreis: str = "Köln",
    regbezirk: str = "Köln",
) -> SEVAS_LEZ_Record:
    return SEVAS_LEZ_Record(
        zone_id=zone_id,
        typ=SEVASZoneType.LEM,
        wert=wert,
        gemeinde=gemeinde,
        kreis=kreis,
        regbezirk=regbezirk,
        shape=shape,
    )


def create_restriction_dataset():
    """
    Creates a synthetic data set consisting of
        1. OSM PBF
        2. SEVAS restrictions that map onto the OSM data
    """

    path = BASE_DATA_DIR / "restriction_test"
    path.mkdir(exist_ok=True)

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
        "AB": (0, {"highway": "tertiary"}),
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

    s = OSMSynthesizer(ascii_map, ways=ways)
    s.to_file(path / "map.pbf")
    r = SEVASSynthesizer(path)

    restrictions = [
        restriction_factory(
            0,
            0,
            0,
            SEVASDir.BOTH,
            SEVASRestrType.HEIGHT,
            "7,5",
            shape=s.way_coordinates("AB"),
            vz=[RestrVZ.VZ_1020_30],
        )
    ]

    r.write_segment_features(restrictions)


def create_road_speeds_dataset():
    """
    Creates a synthetic data set consisting of
        1. OSM PBF
        2. SEVAS road speed segments (dt. Tempozonen Segmente) that map onto the OSM data
    """

    path = BASE_DATA_DIR / "road_speeds_test"
    path.mkdir(exist_ok=True)

    ascii_map = """
A---B---C---D---E---F
"""

    ways = {
        "AB": (0, {"highway": "tertiary"}),
        "BC": (1, {"highway": "tertiary"}),
        "CD": (2, {"highway": "tertiary", "maxspeed": "15"}),
        "DE": (3, {"highway": "tertiary"}),
        "EF": (4, {"highway": "tertiary", "maxweight": "3.5"}),
    }

    s = OSMSynthesizer(ascii_map, ways=ways)
    s.to_file(path / "map.pbf")
    r = SEVASSynthesizer(path)

    preferred_roads = [
        road_speed_factory(0, SEVASRoadSpeedType.PEDESTRIAN, s.way_coordinates("AB")),
        road_speed_factory(1, SEVASRoadSpeedType.CALM_TRAFFIC, s.way_coordinates("BC")),
        road_speed_factory(2, SEVASRoadSpeedType.S20, s.way_coordinates("CD")),
        road_speed_factory(3, SEVASRoadSpeedType.S30, s.way_coordinates("DE")),
        road_speed_factory(4, SEVASRoadSpeedType.URBAN, s.way_coordinates("EF")),
    ]

    r.write_segment_features(preferred_roads)


def create_preferred_road_dataset():
    """
    Creates a synthetic data set consisting of
        1. OSM PBF
        2. SEVAS preferred road segments (dt. Vorrangrouten) that map onto the OSM data
    """

    path = BASE_DATA_DIR / "preferred_road_test"
    path.mkdir(exist_ok=True)

    ascii_map = """
A---B---C---D---E---F
                    |
                    |
        J---I---H---G
"""

    ways = {
        "AB": (0, {"highway": "tertiary"}),
        "BC": (1, {"highway": "tertiary"}),
        "CD": (2, {"highway": "tertiary"}),
        "DE": (3, {"highway": "tertiary"}),
        "EF": (4, {"highway": "tertiary", "maxweight": "3.5"}),
        "FG": (5, {"highway": "tertiary", "maxweight:hgv": "5"}),
        "GH": (6, {"highway": "tertiary", "maxwidth": "6", "hazard": "no"}),
        "HI": (7, {"highway": "tertiary", "maxlength": "1", "hgv": "no"}),
        "IJ": (8, {"highway": "tertiary"}),
    }

    s = OSMSynthesizer(ascii_map, ways=ways)
    s.to_file(path / "map.pbf")
    r = SEVASSynthesizer(path)

    preferred_roads = [SEVASPreferredRoadRecord(0, SEVASDir.BOTH, s.way_coordinates("AB"))]

    r.write_segment_features(preferred_roads)


def create_low_emission_zone_dataset():
    """
    Creates a synthetic data set consisting of
        1. OSM PBF
        2. SEVAS low emission zones

    The relation 1234 denotes the low emission zone in the OSM data,
    while relation 5678 denotes the SEVAS low emission zone. So we expect
    the former to be removed and the latter to be inserted.

    """

    path = BASE_DATA_DIR / "lez_test"
    path.mkdir(exist_ok=True)

    ascii_map = """
             5----------------6
1------------+-------------2  |
|            |             |  |
|  A---B---C-+--D---E---F  |  |
|            |             |  |
4------------+-------------3  |
             |                |
             8----------------7
"""
    # don't really need the ways just check they're still there after the conversion
    ways = {
        "AB": (0, {"highway": "tertiary"}),
        "BC": (1, {"highway": "tertiary"}),
        "CD": (2, {"highway": "tertiary"}),
        "DE": (3, {"highway": "tertiary"}),
        "EF": (4, {"highway": "tertiary"}),
        "12341": (5, {"some": "tag"}),
    }

    relations = [
        SynthRelation(
            0,
            [SynthMember("12341", MemberType.WAY, MemberRole.OUTER)],
            {"boundary": "low_emission_zone", "type": "boundary", "some": "other tag"},
        )
    ]

    s = OSMSynthesizer(ascii_map, ways=ways, relations=relations)
    s.to_file(path / "map.pbf")
    r = SEVASSynthesizer(path)

    # relation 5678 is the SEVAS lez (that's why it's excluded from the osm data)
    low_emission_zones = [low_emission_zone_factory(0, SEVASLEZType.GREEN, [s.way_coordinates("56785")])]

    r.write_low_emission_zones(low_emission_zones)


def create_polygon_reader_data():
    """
    Creates data to test the polygon reader with.
    """

    path = BASE_DATA_DIR / "polygon_reader_test"
    path.mkdir(exist_ok=True)

    ascii_map = """
1----------------2
|      I         |
|      |         |
|      A---B---C-+--D---E---F
|                |
|   G--H         |
|                |
4----------------3
"""
    # don't really need the ways just check they're still there after the conversion
    ways = {
        "AB": (0, {"highway": "tertiary"}),
        "BC": (1, {"highway": "tertiary"}),
        "CD": (2, {"highway": "tertiary"}),
        "DE": (3, {"highway": "tertiary"}),
        "EF": (5, {"highway": "tertiary"}),
        "GH": (6, {"highway": "tertiary"}),
        "AI": (7, {"highway": "tertiary"}),
        "12341": (8, {"boundary": "administrative"}),
    }

    relations = [
        SynthRelation(
            0,
            [SynthMember("12341", MemberType.WAY, MemberRole.OUTER)],
            {
                "boundary": "administrative",
                "type": "boundary",
            },
        )
    ]

    s = OSMSynthesizer(ascii_map, ways=ways, relations=relations)
    s.to_file(path / "map.pbf")


if __name__ == "__main__":
    """
    If this module is called directly, this will create all the fake data sets in test/data/...
    """
    create_restriction_dataset()
    create_preferred_road_dataset()
    create_low_emission_zone_dataset()
    create_polygon_reader_data()
