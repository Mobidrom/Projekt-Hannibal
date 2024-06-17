from pathlib import Path

from osmium.osm import Tag as OsmiumTag

from hannibal.providers.SEVAS.constants import CommonRestrSignatures, RestrVZ
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrRecord

RESTRICTION_PATH = Path("test/data/restriktionen_koeln.dbf")

TEST_HAS_TIME = {4003447: False, 16941331: True, 494470560: False}

TEST_TAGS = {4003447: [OsmiumTag("hgv", "destination"), OsmiumTag("traffic_sign", "DE:253,1020-30")]}

TEST_RESTRICTIONS = {
    16941331: SEVASRestrRecord(
        segment_id=2257785,
        restrkn_id=7972,
        name=None,
        osm_vers="osm_20240404",
        osm_id=16941331,
        fahrtri="0",
        typ="262",
        wert="26",
        tage_einzl="0000000",
        tage_grppe="3",
        zeit1_von="20:00",
        zeit1_bis="06:00",
        zeit2_von=None,
        zeit2_bis=None,
        gemeinde="Köln",
        kreis="Köln",
        regbezirk="Köln",
        vz={
            RestrVZ.VZ_1010_51: False,
            RestrVZ.VZ_1010_57: False,
            RestrVZ.VZ_1010_60: False,
            RestrVZ.VZ_1020_30: False,
            RestrVZ.VZ_1024_12: False,
            RestrVZ.VZ_1024_13: False,
            RestrVZ.VZ_1024_14: False,
            RestrVZ.VZ_1026_31: False,
            RestrVZ.VZ_1026_32: False,
            RestrVZ.VZ_1026_33: False,
            RestrVZ.VZ_1026_34: False,
            RestrVZ.VZ_1026_35: False,
            RestrVZ.VZ_1026_36: False,
            RestrVZ.VZ_1026_37: False,
            RestrVZ.VZ_1026_38: False,
            RestrVZ.VZ_1026_39: False,
            RestrVZ.VZ_1026_62: False,
            RestrVZ.VZ_1048_14: False,
            RestrVZ.VZ_1048_15: False,
            RestrVZ.VZ_1049_13: False,
            RestrVZ.VZ_1053_33: False,
            RestrVZ.VZ_1053_36: False,
            RestrVZ.VZ_1053_37: False,
        },
    ),
    494470560: SEVASRestrRecord(
        segment_id=1969815,
        restrkn_id=7614,
        name="Katharinengraben",
        osm_vers="osm_20240404",
        osm_id=494470560,
        fahrtri="0",
        typ="253",
        wert=None,
        tage_einzl="0000000",
        tage_grppe="0",
        zeit1_von=None,
        zeit1_bis=None,
        zeit2_von=None,
        zeit2_bis=None,
        gemeinde="Köln",
        kreis="Köln",
        regbezirk="Köln",
        vz={
            RestrVZ.VZ_1010_51: False,
            RestrVZ.VZ_1010_57: False,
            RestrVZ.VZ_1010_60: False,
            RestrVZ.VZ_1020_30: True,
            RestrVZ.VZ_1024_12: False,
            RestrVZ.VZ_1024_13: False,
            RestrVZ.VZ_1024_14: False,
            RestrVZ.VZ_1026_31: False,
            RestrVZ.VZ_1026_32: False,
            RestrVZ.VZ_1026_33: False,
            RestrVZ.VZ_1026_34: False,
            RestrVZ.VZ_1026_35: False,
            RestrVZ.VZ_1026_36: False,
            RestrVZ.VZ_1026_37: False,
            RestrVZ.VZ_1026_38: False,
            RestrVZ.VZ_1026_39: False,
            RestrVZ.VZ_1026_62: False,
            RestrVZ.VZ_1048_14: False,
            RestrVZ.VZ_1048_15: False,
            RestrVZ.VZ_1049_13: False,
            RestrVZ.VZ_1053_33: False,
            RestrVZ.VZ_1053_36: False,
            RestrVZ.VZ_1053_37: False,
        },
    ),
}

TEST_SIGNATURES = {
    16941331: "262" + "0" * 23,
    494470560: "25300010000000000000000000",
    4218825: "25300000000000100000000100",
    4003447: CommonRestrSignatures.HGV_NO_DEST_ONLY.value,
}
