import random
from pathlib import Path
from typing import Callable, List, Mapping, Tuple

import pytest

from test.conftest import node_counter
from test.synthesizers.osm import MemberRole, MemberType, OSMSynthesizer, SynthMember, SynthRelation
from test.util.geo import x2lng_m, y2lat_m


def convert_coord(
    coord: Tuple[int, int], grid_size: int = 10, offset: Tuple[float, float] = (0, 0)
) -> Tuple[float, float]:
    return offset[0] + y2lat_m(grid_size * coord[0]), offset[1] + x2lng_m(grid_size * coord[1])


def get_path():
    return Path(f"test/data/osm-synth-test-{str(hash(random.random()))[:12]}.pbf")


COMMON_MAP_PARAMS = (
    ["ascii_map", "nodes"],
    [
        (
            """A--B--C""",
            {
                "A": {"coordinates": (0, 0), "id": 0},
                "B": {"coordinates": (0, 3), "id": 1},
                "C": {"coordinates": (0, 6), "id": 2},
            },
        ),
        (
            """
A--B--C
|  |  |
D--E--F
""",
            {
                "A": {"coordinates": (1, 0), "id": 0},
                "B": {"coordinates": (1, 3), "id": 1},
                "C": {"coordinates": (1, 6), "id": 2},
                "D": {"coordinates": (3, 0), "id": 3},
                "E": {"coordinates": (3, 3), "id": 4},
                "F": {"coordinates": (3, 6), "id": 5},
            },
        ),
        (
            """
    1------------2
    |            |
    |   A--B--C  |
    |   |  |  |  |
    |   D--E--F  | 
    |            |        
    4------------3
""",
            {
                "1": {"coordinates": (1, 4), "id": 0},
                "2": {"coordinates": (1, 17), "id": 1},
                "3": {"coordinates": (7, 17), "id": 9},
                "4": {"coordinates": (7, 4), "id": 8},
                "A": {"coordinates": (3, 8), "id": 2},
                "B": {"coordinates": (3, 11), "id": 3},
                "C": {"coordinates": (3, 14), "id": 4},
                "D": {"coordinates": (5, 8), "id": 5},
                "E": {"coordinates": (5, 11), "id": 6},
                "F": {"coordinates": (5, 14), "id": 7},
            },
        ),
    ],
)

OFFSET_GRIDSIZE_PARAMS = (["gridsize", "offset"], [(12, [52.7, 7.8]), (1, [81.34, -137.34])])


@pytest.mark.parametrize(*COMMON_MAP_PARAMS)
@pytest.mark.parametrize(*OFFSET_GRIDSIZE_PARAMS)
def test_node_coords(
    ascii_map: str, nodes: Mapping[str, str], gridsize: int, offset: Tuple[float, float]
):
    s = OSMSynthesizer(ascii_map, grid_size=gridsize, offset_latlng=offset)
    assert s._nodes.keys() == nodes.keys()

    for k in s._nodes.keys():
        assert s._nodes[k]["id"] == nodes[k]["id"]
        assert pytest.approx(s._nodes[k]["coordinates"], abs=0.1) == convert_coord(
            nodes[k]["coordinates"], gridsize, offset
        )
    p = Path(f"test/data/test_synth_{str(hash(ascii_map))[14:]}.pbf")

    assert not p.exists()

    s.to_file(p)

    assert p.exists()

    p.unlink(True)


@pytest.mark.parametrize(
    ["ascii_map", "nodes", "ways", "relations"],
    [
        (
            """A--B--C""",
            {"A": {"some": "tag"}},
            {"AB": (0, {"highway": "motorway"}), "BC": (1, {"highway": "motorway"})},
            [],
        ),
        (
            """
    1------------2
    |            |
    |   A--B--C  |
    |   |  |  |  |
    |   D--E--F  | 
    |            |        
    4------------3
            """,
            {"A": {"some": "tag"}},
            {
                "AB": (0, {"highway": "motorway"}),
                "BC": (1, {"highway": "motorway"}),
                "AD": (2, {}),
                "DE": (3, {}),
                "EF": (4, {}),
                "1234": (5, {}),
            },
            [SynthRelation(0, [SynthMember("1234", MemberType.WAY, MemberRole.INNER)])],
        ),
    ],
)
@pytest.mark.parametrize(*OFFSET_GRIDSIZE_PARAMS)
def test_object_count(
    ascii_map: str,
    nodes: Mapping[str, Mapping[str, str]],
    ways: Mapping[str, Mapping[str, str]],
    relations: List[SynthRelation],
    gridsize: int,
    offset: Tuple[float, float],
    osm_obj_counter: Callable,
):
    s = OSMSynthesizer(
        ascii_map, nodes=nodes, ways=ways, relations=relations, grid_size=gridsize, offset_latlng=offset
    )
    p = get_path()
    s.to_file(p)
    osm_obj_counter(p, node_counter(ascii_map), len(ways.keys()), len(relations))
    p.unlink()
