from pathlib import Path
from typing import List, Mapping

from osmium import Node, Relation, SimpleHandler, SimpleWriter, Way
from osmium.osm import Tag as OsmiumTag
from osmium.osm import mutable

from hannibal.providers.SEVAS.tables.low_emission_zones import SEVAS_LEZ
from hannibal.providers.SEVAS.tables.preferred_roads import SEVASPreferredRoads
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions
from hannibal.providers.SEVAS.tables.road_speeds import SEVASRoadSpeeds

# it's very unlikely that we'll need to deviate from
# these starting IDs, since it won't make much sense to multiprocess this
# so let's make these static

# default for SEVAS low emission zones
MAX_OSM_ID = 2**63 - 1
# default for SEVAS traffic signs
MAX_SIGN_NODE_ID = 2**62 - 1

NodeLike = Node | mutable.Node
WayLike = Way | mutable.Way
RelationLike = Relation | mutable.Relation


def tags_as_dict(tags: List[OsmiumTag]) -> Mapping[str, str]:
    return {t.k: t.v for t in tags}


class _OSMWriter(SimpleWriter):
    def __init__(self, out_path: Path):
        super(_OSMWriter, self).__init__(str(out_path))
        self.out_path = out_path


class OSMRewriter(SimpleHandler):
    def __init__(
        self,
        in_path: Path,
        out_path: Path,
        restrictions: SEVASRestrictions | None,
        preferred_roads: SEVASPreferredRoads | None,
        road_speeds: SEVASRoadSpeeds | None,
        low_emission_zones: SEVAS_LEZ | None,
        # traffic_signs: SEVASTrafficSigns | None
    ) -> None:
        """
        OSM Handler that rewrites OSM objects from one file to another, modifying existing
        and creating new objects based on passed SEVAS data.
        """
        super(OSMRewriter, self).__init__()

        if not in_path.exists():
            raise FileNotFoundError(f"OSM file {in_path} not found")

        self._in_path = in_path

        self._writer = _OSMWriter(out_path)
        self._restrictions = restrictions
        self._preferred_roads = preferred_roads
        self._road_speeds = road_speeds
        self._low_emission_zones = low_emission_zones
        # self._traffic_signs = traffic_signs

    def node(self, node: Node) -> None:
        """
        Node callback executed for every node in the applied input file.

        Creates a shallow copy and writes it to the output file buffer.

        :param node: an unmutable node from the input file
        """

        mut = node.replace()
        self._add_node(mut)

    def way(self, way: Way) -> None:
        """
        Way callback executed for every way in the applied input file.

        Creates a mutable version of the way with tags replaced in case there is a SEVAS entry
        for this Way.

        :param way: an unmutable way from the input file
        """
        tags = {}
        if self._restrictions and self._restrictions[way.id]:
            for restriction in self._restrictions[way.id]:
                tags.update(restriction.tags())

        if self._preferred_roads and self._preferred_roads[way.id]:
            p = self._preferred_roads[way.id]
            tags.update(p.tag())

        mut = way.replace(tags={**dict(way.tags), **tags})
        self._add_way(mut)

    def relation(self, rel: Relation) -> None:
        """
        Relation callback executed for every relation in the applied input file.

        Creates a shallow copy and writes it to the output file buffer.

        :param relation: an unmutable relation from the input file
        """

        mut = rel.replace()
        self._add_relation(mut)

    def close(self) -> None:
        """Close the writer."""
        self._writer.close()

    def write_low_emission_zones(self) -> None:
        """
        Create new relations from the low emission zones.
        """
        pass

    def write_traffic_signs(self):
        """
        Create new traffic sign nodes.
        """

    def _add_node(self, node: NodeLike) -> None:
        """
        Add a node to the writer.
        """
        self._writer.add_node(node)

    def _add_way(self, way: WayLike) -> None:
        """
        Add a way to the writer.
        """
        self._writer.add_way(way)

    def _add_relation(self, rel: RelationLike) -> None:
        """
        Add a relation to the writer.
        """
        self._writer.add_relation(rel)

    @property
    def in_path(self) -> Path:
        return self._in_path
