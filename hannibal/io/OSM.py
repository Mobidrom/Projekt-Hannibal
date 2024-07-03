import shlex
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

from osmium import SimpleHandler, SimpleWriter
from osmium.geom import WKBFactory
from osmium.osm import RelationMember, mutable
from osmium.osm.types import Node, Relation, Way
from shapely import wkb

from hannibal.config.HannibalConfig import TagCleanConfig
from hannibal.logging import LOGGER
from hannibal.providers.SEVAS.constants import REMOVE_KEYS, SEVASLayer
from hannibal.providers.SEVAS.tables.low_emission_zones import SEVAS_LEZ
from hannibal.providers.SEVAS.tables.preferred_roads import SEVASPreferredRoads
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions
from hannibal.providers.SEVAS.tables.road_speeds import SEVASRoadSpeedRecord, SEVASRoadSpeeds

# it's very unlikely that we'll need to deviate from
# these starting IDs, since it won't make much sense to multiprocess this
# so let's make these static

NodeLike = Node | mutable.Node
WayLike = Way | mutable.Way
RelationLike = Relation | mutable.Relation

OSM_BASIC = {
    "version": 1,
    "changeset": 1,
    "timestamp": "2004-08-16T00:00:00Z",
}  # https://wiki.openstreetmap.org/w/index.php?title=History_of_OpenStreetMap&oldid=1892207#Founding_and_Early_History


class _OSMWriter(SimpleWriter):
    def __init__(self, out_path: Path):
        if out_path.exists():
            LOGGER.warning(f"Removing existing output file at {out_path}")
            out_path.unlink()

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
        tag_clean_config: TagCleanConfig | None = None,
    ) -> None:
        """
        OSM Handler that rewrites OSM objects from one file to another, modifying existing
        and creating new objects based on passed SEVAS data.

        :param in_path: path to the input OSM file
        :param out_path: path to which the new OSM file will be written
        :param restrictions: a SEVAS Restrictions instance
        :param preferred_roads: a SEVAS Preferred roads instance
        :param road_speeds: a SEVAS road speeds instance
        :param low_emission_zones: a SEVAS low emission zones instance
        :param tag_clean_config: a config containing information on which tags to remove on OSM objects
            intersecting with given polygons
        """
        super(OSMRewriter, self).__init__()

        if not in_path.exists():
            raise FileNotFoundError(f"OSM file {in_path} not found")

        self._in_path = in_path
        self.OSMMAP = OSM_BASIC

        self._nodes_file = out_path.parent / "tmp_nodes.pbf"
        self._ways_file = out_path.parent / "tmp_ways.pbf"
        self._rels_file = out_path.parent / "tmp_relations.pbf"
        self._out_file = out_path
        self._node_writer = _OSMWriter(self._nodes_file)
        self._ways_writer = _OSMWriter(self._ways_file)
        self._rels_writer = _OSMWriter(self._rels_file)
        self._restrictions = restrictions
        self._preferred_roads = preferred_roads
        self._road_speeds = road_speeds
        self._low_emission_zones = low_emission_zones
        self._traffic_signs = None
        # self._traffic_signs = traffic_signs

        self._tag_clean_config = tag_clean_config
        self._wkb_fac = WKBFactory()
        # keep some stats

        self._reporter = dict()

        # we categorize the operations that the rewriter performs into
        # the following categories:
        #  1. adding tags
        #  2. overriding tags (meaning adding tags where related tags already exist)
        #  3. cleaning tags (removing tags regardless of whether related tags will be added from SEVAS
        #     data, but based on the clean_tags config options)
        self._reporter["added"] = defaultdict(int)
        self._reporter["overridden"] = defaultdict(int)
        self._reporter["cleaned"] = defaultdict(int)

    def merge(self, delete_tmps: bool = True):
        """
        Merge the node, way and relation files into one

        :param delete_tmps: delete the temporary pbfs
        """

        cmd = f"osmium merge --no-progress -O -o {self._out_file} {self._nodes_file} {self._ways_file} {self._rels_file}"  # noqa
        LOGGER.info("Start merging with osmium")
        proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        std_out, std_err = proc.communicate()
        if std_err:  # pragma: no cover
            LOGGER.critical(std_err)
            raise subprocess.CalledProcessError(1, cmd, std_out, std_err)

        LOGGER.info(f"Done merging to {self._out_file}")
        if not delete_tmps:
            return
        for file in (self._nodes_file, self._ways_file, self._rels_file):
            file.unlink()

    def node(self, node: Node) -> None:
        """
        Node callback executed for every node in the applied input file.

        Creates a shallow copy and writes it to the output file buffer.

        :param node: an unmutable node from the input file
        """
        tags: Mapping[str, str] = dict(node.tags)

        # first check if tags should be cleaned based on
        # whether the node is inside a specified polygon
        if self._intersects_tag_filter(node):
            d = self._filter_tags(tags)
            self._merge_reporter_stats(d)

        # TODO: add traffic sign support
        if self._traffic_signs:
            is_traffic_sign = any([k == "traffic_sign" for k, _ in node.tags])
            if is_traffic_sign:
                self._reporter["overridden"]["traffic_signs"] += 1
                return

        mut = node.replace()
        self._node_writer.add_node(mut)

    def way(self, way: Way) -> None:
        """
        Way callback executed for every way in the applied input file.

        Creates a mutable version of the way with tags replaced in case there is a SEVAS entry
        for this Way.

        :param way: an unmutable way from the input file
        """
        tags: Mapping[str, str] = dict(way.tags)

        if self._intersects_tag_filter(way):
            d = self._filter_tags(tags)
            self._merge_reporter_stats(d)

        # for each layer, we compare the number of tags before and after filtering to report
        # the number of cleaned tags
        n_tags = len(tags)
        if self._restrictions and self._restrictions[way.id]:
            tags = {
                k: v for k, v in tags.items() if not k.startswith(REMOVE_KEYS[SEVASLayer.RESTRICTIONS])
            }
            self._reporter["overridden"]["restrictions"] += int(n_tags != len(tags))
            for restriction in self._restrictions[way.id]:
                self._reporter["added"]["restrictions"] += 1
                tags.update(restriction.tags())

        n_tags = len(tags)
        if self._preferred_roads and self._preferred_roads[way.id]:
            tags = {
                k: v
                for k, v in tags.items()
                if not k.startswith(REMOVE_KEYS[SEVASLayer.PREFERRED_ROADS])
            }
            self._reporter["overridden"]["hgv_designated"] += int(n_tags != len(tags))
            self._reporter["added"]["hgv_designated"] += 1
            p = self._preferred_roads[way.id]
            tags.update(p.tag())

        n_tags = len(tags)
        if self._road_speeds and self._road_speeds[way.id]:
            tags = {
                k: v for k, v in tags.items() if not k.startswith(REMOVE_KEYS[SEVASLayer.ROAD_SPEEDS])
            }
            self._reporter["overridden"]["road_speeds"] += int(n_tags != len(tags))
            self._reporter["added"]["road_speeds"] += 1
            rs = self._road_speeds[way.id]
            strictest: SEVASRoadSpeedRecord = rs[0]
            for road_speed in rs:
                if road_speed.wert > strictest.wert:
                    strictest = road_speed
            tags.update(strictest.tags())

        mut = way.replace(tags=tags)
        self._ways_writer.add_way(mut)

    def _merge_reporter_stats(self, d: Dict[str, int], type: str = "cleaned") -> None:
        for k, v in d.items():
            self._reporter[type][k] += v

    def relation(self, rel: Relation) -> None:
        """
        Relation callback executed for every relation in the applied input file.
        Creates a shallow copy and writes it to the output file buffer.

        If the passed relation represents a low emission zone and the rewriter was passed
        SEVAS low emission zones, the relation is not copied

        :param relation: an unmutable relation from the input file
        """

        # TODO: no spatial check for tag filtering implemented at this point,
        # as relations have an ambiguous geometry type

        if self._low_emission_zones:
            is_low_emission_zone = any(
                [True if k == "boundary" and v == "low_emission_zone" else False for k, v in rel.tags]
            )
            if is_low_emission_zone:
                self._reporter["overridden"]["low_emission_zones"] += 1
                return

        mut = rel.replace()
        self._rels_writer.add_relation(mut)

    def close(self) -> None:
        """Close the writers."""
        self._node_writer.close()
        self._ways_writer.close()
        self._rels_writer.close()

    def write_low_emission_zones(self, start_node_id: int, start_way_id: int, start_rel_id: int) -> None:
        """
        Create new relations from the low emission zones.

        :return: the next unused node ID to be used for traffic signs.
        """

        # low emission zones may be None if no lez layer was found
        if not self._low_emission_zones:
            return start_node_id

        nid = start_node_id
        wid = start_way_id
        rid = start_rel_id

        for lez in self._low_emission_zones.features():
            node_list = []

            for point in lez.shape[0]:  # inner rings don't make much sense here
                self._create_node(nid, point)
                node_list.append(nid)
                nid += 1

            if not node_list[0] == node_list[len(node_list) - 1]:
                LOGGER.warning("Found unclosed low emission zone ring, closing it.")
                node_list.append(node_list[0])
            self._create_way(wid, node_list)
            self._create_relation(rid, [wid], {"boundary": "low_emission_zone"})
            self._reporter["added"]["low_emission_zones"] += 1
            wid += 1
            rid += 1

        return nid + 1

    def write_traffic_signs(self):
        """
        Create new traffic sign nodes.
        """

    def _create_node(self, id: int, location: Tuple[float, float], tags: dict = None):
        """
        Writes a node to the OSM file.

        :param id: the OSM node ID.
        :param location: X, Y tuple of node.
        :param tags: dict of node tags.
        """
        node = mutable.Node(location=location, id=id, tags=tags, **self.OSMMAP)

        try:
            self._node_writer.add_node(node)
        except RuntimeError:
            LOGGER.error("Error adding node {} @ X/Y {}, tags {}".format(id, location, tags))
            raise

    def _create_way(self, id: int, node_ids: List[int], tags: Mapping[str, str] = {}):
        """
        Writes a way to the OSM file.

        :param node_ids: List of ID of nodes in geographical order.
        :type node_ids: list of int or tuple of int

        :param tags: OSM tags to give to the way. Values have to be casted to string.
        :type tags: dict
        """

        way = mutable.Way(nodes=node_ids, tags=tags, id=id, **self.OSMMAP)
        try:
            self._ways_writer.add_way(way)
        except RuntimeError:
            LOGGER.error(f"Error adding way: {id}, Tags: {tags}")
            raise

    def _create_relation(self, id: int, members: List[int], tags: Mapping[str, str] = {}):
        """
        Writes a relation to the OSM file.

        :param members: list of members accepted by osmium.osm.mutable.Relation in the form:
            [(type, id, role), (type, id, role), ...]
        :type members: list of tuple

        :param tags: OSM tags
        :type tags: dict
        """

        relation = mutable.Relation(
            members=self._create_member_list(members), tags=tags, id=id, **self.OSMMAP
        )
        try:
            self._rels_writer.add_relation(relation)
        except RuntimeError:
            LOGGER.error(f"Error adding relation {id}:\nmembers: {members}\ntags: {tags}")
            raise

    def _intersects_tag_filter(self, o: Way | Node | Relation) -> bool:
        if not self._tag_clean_config:
            return False
        wkb_string = None
        if isinstance(o, Node):
            wkb_string = self._wkb_fac.create_point(o)
        elif isinstance(o, Way):
            wkb_string = self._wkb_fac.create_linestring(o)
        else:
            print(type(o))
            raise ValueError(f"Not supporting intersections for object type {o.__class__.__name__}")

        geom = wkb.loads(wkb_string, hex=True)
        return self._tag_clean_config.spatial_check(geom)

    def _filter_tags(self, tags: Dict[str, str]) -> Dict[str, int]:
        """
        Removes entries for tags to be filtered out. Mutates the tag dictionary.

        :param tags: the tag dictionary to be mutated
        :return: the number of tags that were removed
        """

        d = defaultdict(int)
        for k in self._tag_clean_config.keys:
            r = tags.pop(k, None)
            if r:
                d[k] += 1

        return d

    def _create_member_list(self, members: List[int]) -> RelationMember:
        return [RelationMember(m, "w", "outer") for m in members]
