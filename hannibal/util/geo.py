from dataclasses import dataclass
from typing import Dict, Tuple

from shapely import LineString, Point


@dataclass
class Fraction:
    start: float
    end: float
    spoint: Point
    epoint: Point

    def as_dict(self) -> Dict[float, Point]:
        return {self.start: self.spoint, self.end: self.epoint}

    def bounds(self) -> Tuple[float, float]:
        """Start and end fraction"""
        return (self.start, self.end)


def get_fraction(linestring: LineString, other: LineString) -> Fraction:
    """
    Helper function to determine the fraction among _linestring_ that corresponds to _other_. This
    function expects that the following are true:

      1) each point on _other_ is also a point on _linestring_
      2) _other_ is at most of the same length as _linestring_

    :param linestring: a linestring that represents an OSM way
    :param other: a linestring that represents a segment line from a SEVAS data layer. It corresponds
        to _linestring_ because of a matching OSM ID. It may be equal to _linestring_, but may also
        only represent a subset of it
    """
    start_point = Point(other.coords[0])
    end_point = Point(other.coords[len(other.coords) - 1])
    start_frac = float(round(linestring.line_locate_point(start_point, normalized=True), 2))
    end_frac = float(round(linestring.line_locate_point(end_point, normalized=True), 2))

    return Fraction(start_frac, end_frac, start_point, end_point)
