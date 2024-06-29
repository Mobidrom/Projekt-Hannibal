from pathlib import Path
from typing import Callable

import pytest

from test.util.osm import ObjectCounter


def node_counter(ascii_map: str) -> int:
    """
    Little helper for counting the number of expected nodes in an ascii map
    """
    return len([char for char in ascii_map if char.isalnum()])


@pytest.fixture
def osm_obj_counter() -> Callable:
    def counter(p: Path, n: int, w: int, r: int):
        handler = ObjectCounter()
        handler.apply_file(str(p))

        assert n == handler.node_count
        assert w == handler.way_count
        assert r == handler.rel_count

    return counter
