from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, List, Mapping, Tuple

from hannibal.io.DBF import load_dbf
from hannibal.util.immutable import ImmutableMixin


class _RestrAttrs(Enum, str):
    """
    Enum class for relevant restriction attribute names.
    """

    SEGMENT_ID = "segment_id"
    OSM_ID = "OSM_ID"
    FAHRTRI = "FAHRTRI"
    TYP = "TYP"
    WERT = "WERT"
    TAGE_EINZL = "TAGE_EINZL"
    TAGE_GRPPE = "TAGE_GRPPE"
    ZEIT1_VON = "ZEIT1_VON"
    ZEIT1_BIS = "ZEIT1_BIS"
    ZEIT2_VON = "ZEIT2_VON"
    ZEIT2_BIS = "ZEIT2_BIS"


class SEVASRestrRecord(ImmutableMixin):
    """Turn dbf fields into class attributes, so they can be accessed by name."""

    def __init__(self, items: List[Tuple[Any, Any]]):
        """
        A SEVAS Restriction record. Used as a record factory when loading the DBF.
        """

        self.segment_id: int
        self.osm_id: int
        self.fahrtri: int
        self.typ: int
        self.tage_einzl: int
        self.tage_grppe: int
        self.zeit1_von: int
        self.zeit1_bis: int
        self.zeit2_von: int
        self.zeit2_bis: int

        for name, value in items:
            match name:
                case _RestrAttrs.SEGMENT_ID:
                    self.segment_id = value
                case _RestrAttrs.OSM_ID:
                    self.osm_id = value
                case _RestrAttrs.FAHRTRI:
                    self.fahrtri = value
                case _RestrAttrs.TYP:
                    self.typ = value
                case _RestrAttrs.TAGE_EINZL:
                    self.tage_einzl = value
                case _RestrAttrs.TAGE_GRPPE:
                    self.tage_grppe = value
                case _RestrAttrs.ZEIT1_VON:
                    self.zeit1_von = value
                case _RestrAttrs.ZEIT1_BIS:
                    self.zeit1_bis = value
                case _RestrAttrs.ZEIT2_VON:
                    self.zeit2_von = value
                case _RestrAttrs.ZEIT2_BIS:
                    self.zeit2_bis = value
                case _:
                    # no need to handle all fields
                    pass

    def __repr__(self):
        return f"<SEVAS Restriction: id: {self.segment_id}, osm_id: {self.osm_id}>"


class SEVASRestrictions(ImmutableMixin):
    def __init__(self, dbf_path: Path) -> None:
        """
        SEVAS restriction map. The DBF's records are read into memory at initialization by default.

        :param dbf: path to the restriction PBF file.
        """

        self._dbf_path = dbf_path

        # the mapping default value is an empty list
        self._map = Mapping[int, List[SEVASRestrRecord]] = defaultdict(list)

        dbf = load_dbf(self._dbf_path, SEVASRestrictions)

        record: SEVASRestrRecord
        for record in dbf.records:
            self._map[record.osm_id].append()

    def __getitem__(self, key: int) -> List[SEVASRestrRecord] | None:
        """
        Access the internal mapping by OSM ID
        """
        return self._map[key] or None
