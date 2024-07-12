import shlex
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Mapping, Tuple, Type

from osmium import SimpleHandler, SimpleWriter
from osmium.geom import WKBFactory
from osmium.osm import RelationMember, WayNodeList, mutable
from osmium.osm.types import Node, Relation, Way
from shapely import LineString, Point, wkb

from hannibal.config.HannibalConfig import TagCleanConfig
from hannibal.logging import LOGGER
from hannibal.providers.SEVAS.tables.base import SEVASBaseRecord, SEVASBaseTable
from hannibal.providers.SEVAS.tables.low_emission_zones import SEVAS_LEZ
from hannibal.providers.SEVAS.tables.preferred_roads import SEVASPreferredRoads
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions
from hannibal.providers.SEVAS.tables.road_speeds import SEVASRoadSpeeds
from hannibal.util.geo import Fraction, get_fraction

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

FULL_FRACTION = (0.0, 1.0)


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

        In order to speed things up considerably, we make the following assumptions:
            1) most ways in an OSM file do not have corresponding entries in any of the SEVAS
               layers
            2) of the ways that have at least one entry, most SEVAS entries are valid for the whole
               length of the way, meaning the way does not need to be split

        :param way: an unmutable way from the input file
        """
        base_tags: Dict[str, str] = dict(way.tags)
        if self._intersects_tag_filter(way):
            d = self._filter_tags(base_tags)
            self._merge_reporter_stats(d)

        # first, check whether this is a simple copy operation (true if there are no entries
        # for this OSM ID in any SEVAS layer)
        if not self._has_sevas_data(way):
            self._copy_way(way, base_tags)
            return

        # get the way line to find out whether the line needs to be split
        # line = self._wkb_fac.create_linestring(way)
        # geom = wkb.loads(line, hex=True)

        # # a lookup structure to store tags and their start and end fraction of validity
        # split_tags: Dict[Tuple[float, float], Dict[str, str]] = defaultdict(dict)

        # # collect all fractions where the line should be split
        # split_points: Dict[float, Point] = dict()

        # there is at least one entry, but chances are it covers the whole length of the way,
        # so we don't need to split it.
        # if not self._requires_splitting(way.id, geom, split_points, split_tags):
        return self._write_without_splitting(way, base_tags)

        # if we came down here, the way needs to be split into at least two ways.
        # for this, we need the fraction along the way geometry for each node,
        # so we know which nodes belong to which new way.

        # for each layer, we compare the number of tags before and after filtering to report
        # the number of cleaned tags
        # if self._restrictions and self._restrictions[way.id]:
        #     filtered_tags = {
        #         k: v for k, v in tags.items() if not k.startswith(REMOVE_KEYS[SEVASLayer.RESTRICTIONS])
        #     }
        #     self._reporter["overridden"]["restrictions"] += int(len(filtered_tags) != len(tags))
        #     for restriction in self._restrictions[way.id]:
        #         frac: Fraction = get_fraction(geom, restriction.geom)
        #         split_tags[frac.bounds()] = filtered_tags.update(restriction.tags())
        #         split_points.update(frac.as_dict())
        #         self._reporter["added"]["restrictions"] += 1

        # if self._preferred_roads and self._preferred_roads[way.id]:
        #     filtered_tags = {
        #         k: v
        #         for k, v in tags.items()
        #         if not k.startswith(REMOVE_KEYS[SEVASLayer.PREFERRED_ROADS])
        #     }
        #     self._reporter["overridden"]["hgv_designated"] += int(len(filtered_tags) != len(tags))
        #     for preferred_road_segment in self._preferred_roads[way.id]:
        #         frac: Fraction = get_fraction(geom, preferred_road_segment.geom)
        #         split_tags[frac.bounds()] = filtered_tags.update(preferred_road_segment.tag())
        #         split_points.update(frac.as_dict())
        #         self._reporter["added"]["hgv_designated"] += 1

        # if self._road_speeds and self._road_speeds[way.id]:
        #     filtered_tags = {
        #         k: v for k, v in tags.items() if not k.startswith(REMOVE_KEYS[SEVASLayer.ROAD_SPEEDS])
        #     }
        #     self._reporter["overridden"]["road_speeds"] += int(len(filtered_tags) != len(tags))
        #     for road_speed in self._road_speeds[way.id]:
        #         frac: Fraction = get_fraction(geom, road_speed.geom)
        #         split_tags[frac.bounds()] = filtered_tags.update(road_speed.tag())
        #         split_points.update(frac.as_dict())
        #         self._reporter["added"]["road_speeds"] += 1

        # # split the way into multiple
        # splits = sorted(split_points.keys())

        # for start, end in pairwise(splits):
        #     # get all tags valid in this range
        #     valid_tags = {}
        #     for (t_start, t_end), tags in split_tags:
        #         # skip this if no range overlap
        #         if not (start >= t_start or end <= t_end):
        #             continue

        #         # there is a range overlap, so apply the tags
        #         valid_tags.update(tags)

        #     # in many cases, the way will not be split
        #     if start == 0.0 and end == 1.0:
        #         mut = way.replace(tags=valid_tags)
        #         self._ways_writer.add_way(mut)
        #         return

        #     # ...but sometimes ways need to be split
        #     start_node: int
        #     end_node: int

        #     if start == 0.0:
        #         start_node = way.nodes[0].ref
        #     else:
        #         self._create_node()
        #         start_node = 0

        #     if end == 1.0:
        #         end_node = way.nodes[len(way.nodes) - 1].ref
        #     else:
        #         self._create_node()
        #         end_node = 0

    def _has_sevas_data(self, way: Way) -> bool:
        """
        Returns true if the passed OSM Way has at least one entry in one of the SEVAS layers.
        """

        return (
            (self._restrictions and self._restrictions[way.id])
            or (self._preferred_roads and self._preferred_roads[way.id])
            or (self._road_speeds and self._road_speeds[way.id])
        )

    def _write_without_splitting(self, way: Way, base_tags: Dict[str, str]) -> None:
        """
        If there is SEVAS data available for the way, and all of it is valid
        for the whole length of the way, just convert the tags and copy the
        original geometry.
        """

        # go through each available layer that might have an entry for this OSM Way ID
        for layer in self._get_available_way_layers():
            n_tags = len(base_tags)  # noqa

            # remove any tags that relate to this layer.
            # if there is a weight restriction, it is not sufficient to overwrite the existing
            # tag, because there might be an additional "maxweight:conditional" tag that should
            # also be removed
            base_tags = {
                k: v for k, v in base_tags.items() if not k.startswith(layer.invalidating_keys())
            }

            # go through each feature and apply the tags.
            # there is a chance that tags from other SEVAS features will be overwritten in the process
            # but in general, that should only happen in case of badly mapped/illogical SEVAS data
            #  (e.g. a way is both marked as a preferred road but also prohibits access to HGVs)
            feature: SEVASBaseRecord
            for feature in layer[way.id]:
                base_tags.update(feature.tags())

            # TODO: reporter

        mut = way.replace(tags=base_tags)
        self._ways_writer.add_way(mut)

    def _get_available_way_layers(self) -> List[Type[SEVASBaseTable]]:
        """
        Get a list of available SEVAS layers for this conversion that relate to OSM Ways
        (i.e. no low emission zones).
        """
        return [
            layer for layer in [self._restrictions, self._preferred_roads, self._road_speeds] if layer
        ]

    def _requires_splitting(
        self,
        way_id: int,
        way_geom: LineString,
        splits: Dict[float, Point],
        split_tags: Dict[Tuple[float, float], Dict[str, str]],
    ) -> bool:
        """
        Returns true if the way has any corresponding SEVAS entries that do not match the whole
        length of the way geometry.

        Also, stores the found fractions in :param splits: and the relevant tags in :param split_tags:
        so we don't have go through them again
        """
        needs_splitting = False
        for layer in self._get_available_way_layers():
            feature: Type[SEVASBaseRecord]
            for feature in layer[way_id]:
                frac: Fraction = get_fraction(way_geom, feature.geom)
                if frac.bounds() != FULL_FRACTION:
                    needs_splitting = True
                    splits[frac.start] = frac.spoint
                    splits[frac.end] = frac.epoint
                split_tags[frac.bounds()].update(feature.tags())
        return needs_splitting

    def _get_way_fractions(self, nodes: WayNodeList, way_geom: LineString) -> Dict[int, float]:
        """
        Calculate the fraction along an OSM Way's geometry for each constituent node.
        """
        result = {}
        for node in nodes:
            as_wkb = self._wkb_fac.create_point(node.location)
            p = wkb.loads(as_wkb, hex=True)
            fraction = way_geom.line_locate_point(p, normalized=True)
            result[node.ref] = fraction

        return result

    def _copy_way(self, way: Way, tags: Dict[str, str]):
        """
        Simply copy the way over to the output file. Will be the case for most ways in the input file.

        :param way: an OSM way object
        :param tags: the tags to use instead of the way's original tags
        """
        mut = way.replace(tags=tags)
        self._ways_writer.add_way(mut)

    def _merge_reporter_stats(self, d: Dict[str, int], type: str = "cleaned") -> None:
        for k, v in d.items():
            self._reporter[type][k] += v

    def _way_nodes(self, line: LineString, nodes: WayNodeList) -> List[Tuple[int, float]]:
        """
        Calculates the fraction along an OSM Way for each constituing node.

        :param line: an OSM Way geometry
        :param nodes: the OSM Way's node list

        Returns a list of tuples containing
            1) the Node ID
            2) the Node's fraction (i.e. "percent along") the way
        """

        fracs = []
        for node in nodes:
            geom = self._wkb_fac.create_point(node)
            p = wkb.loads(geom, hex=True)
            frac = float(round(line.line_locate_point(p, normalized=True), 2))
            fracs.append(node.ref, frac)

        return fracs

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
