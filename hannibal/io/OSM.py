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
        start_node_id: int,
        start_way_id: int,
        start_rel_id: int,
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

        # for interfacing osmium with shapely
        self._wkb_fac = WKBFactory()

        self._next_node_id = start_node_id
        self._next_way_id = start_way_id
        self._next_rel_id = start_rel_id

        # keep some stats
        self._reporter = dict()

        # we categorize the operations that the rewriter performs into
        # the following categories:
        #  1. adding tags
        #  2. overriding tags (meaning adding tags where related tags already exist)
        #  3. cleaning tags (removing tags regardless of whether related tags will be added from SEVAS
        #     data, but based on the clean_tags config options)
        # self._reporter["added"] = defaultdict(int)
        # self._reporter["overridden"] = defaultdict(int)
        # self._reporter["cleaned"] = defaultdict(int)
        self._reporter["uninteresting"] = 0
        self._reporter["written"] = 0
        self._reporter["split"] = 0

    def merge(self, delete_tmps: bool = True):
        """
        Merge the node, way and relation files into one. Calls osmium merge first, then osmium sort.
        Requires osmium-tools to be installed.

        :param delete_tmps: delete the temporary pbfs
        """

        files_sorted = []

        # insertion of new nodes and ways due to splitting along SEVAS geometries
        # messes up sort order which is required for osmium merge to work
        for file in (self._nodes_file, self._ways_file, self._rels_file):
            file_sorted = file.parent / f"{file.stem}_sorted{file.suffix}"
            files_sorted.append(file_sorted)
            sort_cmd = f"osmium sort --no-progress -O -o {file_sorted} {file}"
            proc = subprocess.Popen(
                shlex.split(sort_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            std_out, std_err = proc.communicate()
            if std_err:  # pragma: no cover
                LOGGER.critical(std_err)
                raise subprocess.CalledProcessError(1, sort_cmd, std_out, std_err)

        LOGGER.info("Done sorting OSM files.")

        cmd = f"osmium merge --no-progress -O -o {self._out_file} {' '.join([str(f) for f in files_sorted])}"  # noqa
        LOGGER.info("Start merging with osmium")
        proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        std_out, std_err = proc.communicate()
        if std_err:  # pragma: no cover
            LOGGER.critical(std_err)
            raise subprocess.CalledProcessError(1, cmd, std_out, std_err)

        LOGGER.info(f"Done merging to {self._out_file}")
        if not delete_tmps:
            return
        for file in (self._nodes_file, self._ways_file, self._rels_file, *files_sorted):
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
            d = self._filter_tags(tags)  # noqa
            # self._merge_reporter_stats(d)

        # TODO: add traffic sign support
        if self._traffic_signs:
            is_traffic_sign = any([k == "traffic_sign" for k, _ in node.tags])
            if is_traffic_sign:
                # self._reporter["overridden"]["traffic_signs"] += 1
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
            # regardless of whether or not the way will be split, we filter out the tags
            # that the user wants to remove from the resulting data set
            d = self._filter_tags(base_tags)  # noqa
            # self._merge_reporter_stats(d)

        # first, check whether this is a simple copy operation (true if there are no entries
        # for this OSM ID in any SEVAS layer)
        if not self._has_sevas_data(way):
            self._copy_way(way, base_tags)
            self._reporter["uninteresting"] += 1
            return

        # get the way line to find out whether the line needs to be split
        line = self._wkb_fac.create_linestring(way)
        geom = wkb.loads(line, hex=True)

        # a lookup structure to store the features keyed by their validity along the
        # original way
        feature_splits: Dict[Tuple[float, float], Type[SEVASBaseRecord]] = dict()

        # collect all fractions where the line should be split
        split_points: Dict[float, Point] = dict()

        # there is at least one entry, but chances are it covers the whole length of the way,
        # so we don't need to split it.
        if self._requires_splitting(way.id, geom, split_points, feature_splits):
            self._reporter["split"] += 1
            self._split_way(way, geom, split_points, feature_splits, base_tags)
        else:
            self._reporter["written"] += 1
            self._write_without_splitting(way, base_tags)

    def _has_sevas_data(self, way: Way) -> bool:
        """
        Returns true if the passed OSM Way has at least one entry in one of the SEVAS layers.
        """

        return (
            (self._restrictions and self._restrictions[way.id])
            or (self._preferred_roads and self._preferred_roads[way.id])
            or (self._road_speeds and self._road_speeds[way.id])
        )

    def _split_way(
        self,
        way: Way,
        way_geom: LineString,
        splits: Dict[float, Point],
        feature_splits: Dict[Tuple[float, float], Type[SEVASBaseRecord]],
        tags: Dict[str, str],
    ):
        """
        The way needs to be split into two or more new ways.

        :param way: the OSM Way to be split
        :param way_geom: the way's geometry
        :param splits: the splits along the original way (e.g. 0.33 for 33%
            along the way's length) and the respective point geometries
        :param feature_splits: the SEVAS features keyed by the splits along which they are valid
        :param tags: the way's tags (already cleaned of user prescribed keys)
        """

        nodes = self._get_way_node_splits(way.nodes, way_geom)

        # walk through the splits and update the tags from the split_tags dictionary
        # where the range overlaps

        last_node_split = 0.0
        last_node_id = None

        # the splits don't contain the start or end of the original geometry
        # as these are implicit
        for split, split_point in splits.items():
            node_ids = []

            # after the first iteration, the last node should be truthy
            if last_node_id:
                node_ids.append(last_node_id)
            # get the nodes that belong to this fraction
            split_at_node = False
            for node_id, node_fraction in nodes.items():
                # we are only interested in nodes between the last and current split point
                if node_fraction < last_node_split or node_fraction > split:
                    continue

                node_ids.append(node_id)
                # way happens to be split exactly at node
                if node_fraction == split:
                    split_at_node = True

            # if there is no node at the split yet, we create it
            if not split_at_node:
                self._create_node(self._next_node_id, tuple(*split_point.coords))
                node_ids.append(self._next_node_id)
                last_node_id = self._next_node_id
                self._next_node_id += 1

            # get the features for this split
            valid_features = self._get_feature_splits(feature_splits, last_node_split, split)
            valid_tags = dict(tags)
            for feat in valid_features:
                # remove keys that collide with SEVAS tags
                valid_tags = {
                    k: v for k, v in tags.items() if not k.startswith(feat.invalidating_keys())
                }
                # add SEVAS tags
                valid_tags.update(feat.tags())

            # create the way
            self._create_way(self._next_way_id, node_ids, valid_tags)
            self._next_way_id += 1

            # save the last split so we know where we stopped in the next iteration
            last_node_split = split

        # finally, add the way from the last split to the end of the way
        node_ids = [last_node_id]

        # get the nodes that belong to this fraction
        # (at this point no new nodes will be created because the last node will actually be the
        # original end node)
        for node_id, node_fraction in nodes.items():
            # we are only interested in nodes after the last split
            if node_fraction < last_node_split:
                continue

            node_ids.append(node_id)

        # get the features for this split
        valid_features = self._get_feature_splits(feature_splits, last_node_split, 1.0)
        valid_tags = dict(tags)
        for feat in valid_features:
            # remove keys that collide with SEVAS tags
            valid_tags = {k: v for k, v in tags.items() if not k.startswith(feat.invalidating_keys())}
            # add SEVAS tags
            valid_tags.update(feat.tags())

        # create the way
        self._create_way(self._next_way_id, node_ids, valid_tags)
        self._next_way_id += 1

    def _get_feature_splits(
        self, feature_splits: Dict[Tuple[float, float], Type[SEVASBaseRecord]], start: float, end: float
    ) -> List[Type[SEVASBaseRecord]]:
        """
        Retrieves the tags that are valid for the given split from :param start: to :param end: from
            a mapping {(start, end): feature}.
        """
        valid_features: List[Type[SEVASBaseRecord]] = []
        for frac, feature in feature_splits.items():
            split_start, split_end = frac
            if start < split_end and end > split_start:
                valid_features.append(feature)

        return valid_features

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
            if not layer[way.id]:
                continue
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
        feature_splits: Dict[Tuple[float, float], Type[SEVASBaseRecord]],
    ) -> bool:
        """
        Returns true if the way has any corresponding SEVAS entries that do not match the whole
        length of the way geometry.

        Also stores the found fractions in :param splits: and the splitting feature in
        :param feature_splits: so we don't have go through them again in case we need to split
        """
        needs_splitting = False
        for layer in self._get_available_way_layers():
            feature: Type[SEVASBaseRecord]
            if not layer[way_id]:
                continue
            for feature in layer[way_id]:
                frac: Fraction = get_fraction(way_geom, feature.geom)
                if frac.is_full() or not frac.is_valid():
                    continue

                needs_splitting = True
                if frac.start != 0.0:
                    splits[frac.start] = frac.spoint

                if frac.end != 1.0:
                    splits[frac.end] = frac.epoint
                feature_splits[frac.bounds()] = feature
        return needs_splitting

    def _get_way_node_splits(self, nodes: WayNodeList, way_geom: LineString) -> Dict[int, float]:
        """
        Calculate the fraction along an OSM Way's geometry for each constituent node.
        """
        result = {nodes[0].ref: 0.0, nodes[len(nodes) - 1].ref: 1.0}
        for node_id in range(1, len(nodes) - 1):
            node = nodes[node_id]
            as_wkb = self._wkb_fac.create_point(node.location)
            p = wkb.loads(as_wkb, hex=True)
            fraction = float(way_geom.line_locate_point(p, normalized=True))
            result[node.ref] = fraction

        return dict(sorted(result.items(), key=lambda s: s[1]))

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
                # self._reporter["overridden"]["low_emission_zones"] += 1
                return

        mut = rel.replace()
        self._rels_writer.add_relation(mut)

    def close(self) -> None:
        """Close the writers."""
        self._node_writer.close()
        self._ways_writer.close()
        self._rels_writer.close()

    def write_low_emission_zones(self) -> None:
        """
        Create new relations from the low emission zones.

        :return: the next unused node ID to be used for traffic signs.
        """

        # low emission zones may be None if no lez layer was found
        if not self._low_emission_zones:
            return

        for lez in self._low_emission_zones.features():
            node_list = []

            for point in lez.shape[0]:  # inner rings don't make much sense here
                self._create_node(self._next_node_id, point)
                node_list.append(self._next_node_id)
                self._next_node_id += 1

            if not node_list[0] == node_list[len(node_list) - 1]:
                LOGGER.warning("Found unclosed low emission zone ring, closing it.")
                node_list.append(node_list[0])
            self._create_way(self._next_way_id, node_list)
            self._create_relation(
                self._next_rel_id, [self._next_way_id], {"boundary": "low_emission_zone"}
            )
            # self._reporter["added"]["low_emission_zones"] += 1
            self._next_way_id += 1
            self._next_rel_id += 1

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
