from math import atan, exp, pi

RAD_EARTH_METERS = 6378160
DEG_PER_RAD = 57.29577951308232


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
