from collections import defaultdict
from typing import Mapping, Tuple

from osmium import Node, Relation, SimpleHandler, Way


class TagCounter(SimpleHandler):
    def __init__(self, tags: Mapping[Tuple[str, str, str], int]) -> None:
        """
        A simpler OSM file handler that counts tags passed via the constructor.

        :param tags: a dictionary that maps tags ( object type, tag key **and** value)
            to their expected occurence.
        """
        super().__init__()

        self._tags = tags
        self._counter = defaultdict(int)

    def node(self, n: Node):
        self._count_tags(n)

    def way(self, w):
        self._count_tags(w)

    def relation(self, r):
        self._count_tags(r)

    def _count_tags(self, o: Node | Way | Relation):
        # node, way, relation
        o_type = o.__class__.__name__.lower()

        for tag in o.tags:
            self._counter[(o_type, tag.k, tag.v)] += 1

    @property
    def counter(self):
        return self._counter


class ObjectCounter(SimpleHandler):
    def __init__(self) -> None:
        """
        A simple Handler that counts OSM objects in a file by type (n/w/r).
        """

        super().__init__()
        self._nc = 0
        self._wc = 0
        self._rc = 0

    @property
    def node_count(self):
        return self._nc

    @property
    def way_count(self):
        return self._wc

    @property
    def rel_count(self):
        return self._rc

    def node(self, n):
        self._nc += 1

    def way(self, w):
        self._wc += 1

    def relation(self, r):
        self._rc += 1
