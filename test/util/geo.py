from math import atan, exp, pi
from typing import List

import pytest
from shapely import LineString

RAD_EARTH_METERS = 6378160
DEG_PER_RAD = 57.29577951308232


def line_in_list(line: LineString, line_list: List[LineString]):
    """
    Small helper that tests whether a given line is in a given list exactly once.
    """
    __tracebackhide__ = True

    found = 0
    for other_line in line_list:
        if line.equals_exact(other_line, 0.0001):
            found += 1

    if not found == 1:
        pytest.fail(f"Expected exactly one occurence of {line} in {line_list}, found {found}.")


def y2lat_m(y: float) -> float:
    """
    **Approximate** conversion of a distance given in meters along
    the earth's latitudinal axis to degrees. Should only be used for testing.
    """
    return (2 * atan(exp(y / RAD_EARTH_METERS)) - pi / 2) * DEG_PER_RAD


def x2lng_m(x: float) -> float:
    """
    **Approximate** conversion of a distance given in meters along the earth's longitudinal
    axis to degrees. Should only be used for testing.
    """
    return (x / RAD_EARTH_METERS) * DEG_PER_RAD
