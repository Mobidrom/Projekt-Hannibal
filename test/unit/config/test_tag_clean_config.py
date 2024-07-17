import inspect
import json

import pytest
from shapely import Point, Polygon
from shapely.geometry import shape

from hannibal.config.HannibalConfig import TagCleanConfig


@pytest.fixture()
def polygon() -> Polygon:
    with open("test/data/test_poly.geojson") as fh:
        f = json.loads(fh.read())

    return shape(f["features"][0]["geometry"])


def test_square_split():
    c = TagCleanConfig(0, ["foo"], Polygon(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))))
    default_min = inspect.signature(c._evenly_split_polygons).parameters["min_num"].default
    sub_divisions = c._evenly_split_polygons()
    assert len(sub_divisions) >= default_min + 1

    i = 0
    while i < len(sub_divisions) - 1:
        this_ = sub_divisions[i]
        next_ = sub_divisions[i + 1]
        assert pytest.approx(this_.area, abs=0.001) == next_.area
        i += 1


def test_polygon_split(polygon: Polygon):
    c = TagCleanConfig(0, ["foo"], polygon)
    default_min = inspect.signature(c._evenly_split_polygons).parameters["min_num"].default
    sub_divisions = c._evenly_split_polygons()
    assert len(sub_divisions) >= default_min + 1


@pytest.mark.parametrize(
    ["point", "should_intersect"],
    [(Point(6.9456, 50.9317), True), (Point(0, 0), False), (Point(6.8944, 50.9113), False)],
)
def test_intersections(polygon: Polygon, point: Point, should_intersect: bool):
    c = TagCleanConfig(0, ["foo"], polygon)
    assert c.spatial_check(point) == should_intersect
