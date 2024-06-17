from pathlib import Path

from osmium import Node, Relation, SimpleHandler, SimpleWriter, Way
from osmium.osm import mutable

from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions


class _OSMWriter(SimpleWriter):
    def __init__(self, out_path: Path):
        super(_OSMWriter, self).__init__(out_path)


class OSMRewriter(SimpleHandler):
    def __init__(self, in_path: Path, out_path: Path, restrictions: SEVASRestrictions) -> None:
        """
        OSM Handler that rewrites OSM objects from one file to another, possibly modifying some
        """
        super(OSMRewriter, self).__init__()

        if not in_path.exists():
            raise FileNotFoundError(f"OSM file {in_path} not found")

        self._in_path = in_path
        self._writer = _OSMWriter(out_path)
        self._restrictions = restrictions

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
        mut = way.replace()
        self._add_way(mut)

    def relation(self, rel: Relation) -> None:
        """
        Relation callback executed for every relation in the applied input file.

        Creates a shallow copy and writes it to the output file buffer.

        :param relation: an unmutable relation from the input file
        """
        # TODO(chris): replace Low Emission zone relations, figure out which ones to skip

        mut = rel.replace()
        self._add_relation(mut)

    def close(self) -> None:
        """Close the writer."""
        self._writer.close()

    def _add_node(self, node: mutable.NodeLike) -> None:
        """
        Add a node to the writer.
        """
        self._writer.add_node(node)

    def _add_way(self, way: mutable.WayLike) -> None:
        """
        Add a way to the writer.
        """
        self._writer.add_way(way)

    def _add_relation(self, rel: mutable.RelationLike) -> None:
        """
        Add a relation to the writer.
        """
        self._writer.add_relation(rel)

    @property
    def in_path(self) -> Path:
        return self._in_path
