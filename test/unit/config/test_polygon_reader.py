from hannibal.io.PolygonReader import PolygonReader
from test import BASE_DATA_DIR


def test_geometry():
    path = BASE_DATA_DIR / "polygon_reader_test/map.pbf"

    r = PolygonReader(0)
    r.apply_file(str(path))

    assert r.geometry
    assert r.geometry.area > 0
    assert r.geometry.is_valid
    assert not r.geometry.is_empty
