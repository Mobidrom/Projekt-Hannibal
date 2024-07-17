from collections import defaultdict
from typing import Dict, List

import shapely.wkb as wkblib
from osmium import Node, Relation, SimpleHandler, Way
from osmium.geom import WKBFactory
from shapely import LineString


class OSMTestHandler(SimpleHandler):
    def __init__(self) -> None:
        """
        A simpler OSM file handler that counts tags and reads geometries for testing purposes.
        """
        super().__init__()

        self._tag_counter = defaultdict(int)
        self.node_count = 0
        self.way_count = 0
        self.relation_count = 0
        self.way_shapes: Dict[str, List[LineString]] = defaultdict(list)
        self.wkb_fac = WKBFactory()

    def node(self, n: Node):
        self._count_tags(n)
        self.node_count += 1

    def way(self, w: Way):
        self._count_tags(w)
        self.way_count += 1

        self.way_shapes[w.tags["name"]].append(wkblib.loads(self.wkb_fac.create_linestring(w)))

    def relation(self, r):
        self._count_tags(r)
        self.relation_count += 1

    def _count_tags(self, o: Node | Way | Relation):
        # node, way, relation
        o_type = o.__class__.__name__.lower()

        for tag in o.tags:
            self._tag_counter[(o_type, tag.k, tag.v)] += 1

    @property
    def counter(self):
        return self._tag_counter
