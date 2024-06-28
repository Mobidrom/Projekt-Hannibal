from dataclasses import dataclass, field
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import List, Mapping, Tuple

from osmium import SimpleWriter
from osmium.osm.mutable import Node, Relation, Way

from test.util.geo import x2lng_m, y2lat_m

TAG_BASE = {
    "version": 1,
    "changeset": 1,
    "timestamp": "2056-08-16T00:00:00Z",
}


@dataclass
class SynthNode:
    tags: Mapping[str, str] = field(default_factory=dict)


@dataclass
class SynthWay:
    nodes: str
    tags: Mapping[str, str] = field(default_factory=dict)


class MemberRole(str, Enum):
    INNER = "inner"
    OUTER = "outer"


class MemberType(str, Enum):
    WAY = "w"
    NODE = "n"
    RELATION = "r"


@dataclass
class SynthMember:
    name: str
    type: MemberType
    role: MemberRole


@dataclass
class SynthRelation:
    id: int
    members: List[SynthMember]
    tags: Mapping[str, str] = field(default_factory=dict)


class OSMSynthesizer:
    def __init__(
        self,
        ascii_map: str,
        nodes: Mapping[str, Mapping[str, str]] = {},
        ways: Mapping[str, Tuple[int, Mapping[str, str]]] = {},
        relations: List[SynthRelation] = [],
        grid_size: int = 10,
        offset_latlng: Tuple[int, int] = (0, 0),
    ) -> None:
        """
        A class that helps you create fake OSM data sets!

        :param ascii_map: an ascii-art style map, where alphanumerical characters denote nodes
        :param nodes: a dictionary of nodes, keys are node names, values are its tags
        :param ways: a dictionary of ways, the key is the string containing the constituent node names,
            values are its id and its tags
        :param relations: a list of relations
        :param grid_size: the size in meters of a single character in the ascii grid
        :param offset_latlng: the offset of the top left corner of the ascii map in degrees
        """
        self._node_tags = nodes
        self._nodes = {}
        self._ways = ways
        self._relations = relations
        self._grid_size = grid_size
        self._ll_offset = offset_latlng
        self._nrows = 0

        id_ = 0
        for line in StringIO(ascii_map):
            for col, char in enumerate(line):
                if not char.isalpha() and not char.isnumeric():
                    continue

                self._nodes[char] = {
                    "coordinates": (
                        self._ll_offset[0] - y2lat_m(self._grid_size * self._nrows),
                        self._ll_offset[1] + x2lng_m(self._grid_size * col),
                    ),
                    "id": id_,
                }
                id_ += 1
            self._nrows += 1

    def way_coordinates(self, name: str) -> List[Tuple[float, float]]:
        """
        Get way coordinates by name.

        :param: the node members concatenated into a string, like "ABC"
        :return: the list of coordinates in lat/lng order
        """

        try:
            return [self._nodes[c]["coordinates"] for c in name]
        except KeyError:
            raise KeyError("Unable to find node by name")

    def to_file(self, path: Path):
        """
        Write the OSM data to a file. Uses pyosmium.
        """
        path.unlink(True)
        writer = SimpleWriter(str(path))

        # start with nodes
        for nname, node in self._nodes.items():
            n = Node(
                location=(node["coordinates"][1], node["coordinates"][0]),
                tags=self._node_tags.get(nname, {}),
                id=node["id"],
            )
            writer.add_node(n)

        # then ways
        for wname, (id_, tags) in self._ways.items():
            w = Way(nodes=[self._nodes[c]["id"] for c in wname], tags=tags, id=id_)
            writer.add_way(w)

        # then relations
        for id_, rel in enumerate(self._relations):
            members = []
            for member in rel.members:
                t = member.type.value
                mid_: int

                # collect the member ids
                match t:
                    case MemberType.WAY:
                        mid_ = self._ways.get(member.name)[0]
                    case MemberType.NODE:
                        mid_ = self._nodes[member.name]["id"]
                    case MemberType.RELATION:
                        raise NotImplementedError(
                            "Relation member type relation currently not supported"
                        )
                members.append((member.type.value, mid_, member.role.value))
            rel = Relation(members=members, tags=rel.tags, id=id_)
            writer.add_relation(rel)

        writer.close()
