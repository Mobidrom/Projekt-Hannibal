from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Generator, List, Mapping, Tuple

from osmium.osm import Tag as OsmiumTag

from hannibal.io.DBF import load_dbf
from hannibal.logging import LOGGER
from hannibal.providers import HannibalProvider
from hannibal.providers.SEVAS.constants import (
    DAYS_OF_WEEK,
    DIMENSIONAL_RESTRICTION_TYPES,
    EXEMPTORS,
    INVALID_TAGE_EINZL,
    NO_TAGE_EINZL,
    NON_KEYABLE,
    PERMISSIVE_VALUES,
    SPECIAL_VZ,
    SPECIFIERS,
    TRAFFIC_MODES,
    CommonRestrSignatures,
    RestrVZ,
    SEVASRestrType,
)
from hannibal.util.data import str_to_bool
from hannibal.util.exception import HannibalSchemaError
from hannibal.util.immutable import ImmutableMixin


class SEVASDir(str, Enum):
    BOTH = "0"
    FORW = "1"
    BACKW = "2"


class SEVASGroupedDays(str, Enum):
    NONE = "0"
    DAILY = "1"
    WEEKDAYS = "2"
    SUNDAYS_HOLIDAYS = "3"


KEY_FROM_TYPE = {
    SEVASRestrType.HGV_NO: "hgv",
    SEVASRestrType.WEIGHT: "maxweight",
    SEVASRestrType.HEIGHT: "maxheight",
    SEVASRestrType.LENGTH: "maxlength",
    SEVASRestrType.HAZMAT: "hazmat",
    SEVASRestrType.WIDTH: "maxwidth",
    SEVASRestrType.AXLE_LOAD: "maxaxleload",
    SEVASRestrType.HAZMAT_WATER: "hazmat:water",
    SEVASRestrType.HGV_TRAILER: "hgv:trailer",
}

DEST_ONLY_MODIFIABLE = [
    SEVASRestrType.WEIGHT,
    SEVASRestrType.HEIGHT,
    SEVASRestrType.LENGTH,
    SEVASRestrType.HAZMAT,
    SEVASRestrType.WIDTH,
    SEVASRestrType.AXLE_LOAD,
    SEVASRestrType.HAZMAT_WATER,
    SEVASRestrType.HGV_TRAILER,
]


def SEVASRestrFactory(items: List[Tuple[Any, Any]]):
    kwargs = {k: v for k, v in items if not k.startswith("vz_")}
    vz = {RestrVZ(k): str_to_bool(v) for k, v in items if k.startswith("vz_")}

    return SEVASRestrRecord(**kwargs, vz=vz)


@dataclass
class SEVASRestrRecord:
    """
    The SEVAS Restriction class. DBF fields into attributes, so they can be accessed by name.
    The "vz_" flags are stored in their own dictionary.

    """

    segment_id: int
    restrkn_id: int
    name: str
    osm_id: int
    osm_vers: int
    fahrtri: int
    typ: int
    wert: str | None
    tage_einzl: str | None
    tage_grppe: str | None
    zeit1_von: str | None
    zeit1_bis: str | None
    zeit2_von: str | None
    zeit2_bis: str | None
    gemeinde: str
    kreis: str
    regbezirk: str

    # collect the additional signs in a separate map
    vz: Mapping[RestrVZ, bool]

    def get_vz_items_sorted(self) -> Tuple[RestrVZ, bool]:
        return sorted(self.vz.items(), key=lambda i: str(i[0]))

    def has_time_case(self) -> bool:
        """
        Whether or not this restriction has a time component.
        """
        return (
            self.zeit1_bis != ""
            or self.tage_einzl != NO_TAGE_EINZL
            or (
                self.tage_grppe != SEVASGroupedDays.NONE
                # really no need to consider "every day" as a special case
                and self.tage_grppe != SEVASGroupedDays.DAILY
            )
        )

    def is_basic(self):
        """
        A restriction is considered basic if it has no additional signs that modify
        the restriction's scope (but may still have a time case).
        """
        return len(self.get_vz()) == 0

    def sign_signature(self):
        """
        In order to identify common combinations of type and vz_ flags, a "sign_signature" field
        is created that is a string of length 26 composed of the type string (first 3 chars)
        and its flags ("0" or "1" for each of the 23 flags).

        Example signature:

                2530000000000000000100000
                (t)(-------flags--------)

        """
        return "".join([self.typ, *["1" if v else "0" for k, v in self.get_vz_items_sorted()]])

    def get_traffic_sign_tag(self) -> OsmiumTag:
        """
        OSM allows traffic_sign tags on ways that specify the exact traffic sign (including all its
        components) to be documented along the ways where it's valid.
        """
        return OsmiumTag(
            "traffic_sign",
            f"DE:{','.join([str(self.typ), *[str(v.value)[3:].replace("_", "-") for
                                              v in self.get_vz() if v]])}",
        )

    def is_dimensional_type(self) -> bool:
        return self.type in DIMENSIONAL_RESTRICTION_TYPES

    def is_special_signature(self) -> bool:
        """
        Some signatures are common but not easily represented in OSM tags.

        These are handled "single-handedly", so this tells us whether this restriction
        is one of such cases. We generally only consider a restriction special if it
        has at least one additional sign, otherwise it's easy to handle.
        """
        return self.sign_signature() in [
            s.value for s in CommonRestrSignatures if s.value[3:] != 23 * "0"
        ]

    def get_vz(self) -> List[RestrVZ]:
        """
        Get all additional signs that apply to this restriction.
        """
        return [k for k, v in self.vz.items() if v]

    def get_exemptors(self) -> List[RestrVZ]:
        """
        Get all additional signs that apply to this restriction and fall under the exemptor category
        (meaning they exempt certain traffic from the restriction).
        """
        return [k for k, v in self.vz.items() if v and k in EXEMPTORS]

    def get_specifiers(self) -> List[RestrVZ]:
        """
        Get all additional signs that apply to this restriction and fall under the specifier category
        (meaning the restriction only applies to certain traffic from the restriction).
        """
        return [k for k, v in self.vz.items() if v and k in SPECIFIERS]

    def get_special_vz(self) -> List[RestrVZ]:
        """
        Get all additional signs that apply to this restriction and are neither exemptors nor
        specifiers.
        """
        return [k for k, v in self.vz.items() if v and k in SPECIAL_VZ]

    def exemptor_count(self):
        """
        Get the number of additional signs that are exemptors.

        Exemptors are those signs that make the restriction not valid
        for a specific type of traffic (vehicle type, destination only, etc.).
        """
        return len(self.get_exemptors())

    def specifier_count(self):
        """
        Get the number of additional signs that are specifiers.

        Specifiers are those signs that make the restriction only valid for
        a specific type of traffic (vehicle type, destination only, etc.)
        """
        return len(self.get_specifiers())

    def special_vz_count(self):
        """
        These are the number of additional signs that can not be freely combinated
        easily, so they are handled separately
        """
        return len(self.get_special_vz())

    def tags(self):
        if self.is_special_signature():
            return [*self.get_special_signature_tags(), self.get_traffic_sign_tag()]
        if self.exemptor_count() and self.specifier_count():
            if self.special_vz_count():
                LOGGER.warn(
                    f"Restriction has exemption, specification and special case: {self.segment_id}"
                )
            else:
                return [
                    *self.get_exemptor_tags(),
                    *self.get_specifier_tags(),
                    self.get_traffic_sign_tag(),
                ]
        elif self.exemptor_count() and self.special_vz_count():
            LOGGER.warn(
                f"Restriction has exemption and special case: {self.segment_id}, {self.sign_signature()}"
                ", falling back to default."
            )
        elif self.exemptor_count():  # only exemption cases
            return [self.get_basic_tag(), *self.get_exemptor_tags(), self.get_traffic_sign_tag()]
        elif self.specifier_count():
            if self.special_vz_count():
                LOGGER.warn(f"Restriction has special case: {self.segment_id}")
            else:
                return [*self.get_specifier_tags(), self.get_traffic_sign_tag()]

        return [self.get_basic_tag(), self.get_traffic_sign_tag()]

    def get_exemptor_tags(self) -> List[OsmiumTag]:
        """
        Get the tags based on the restriction's exemptors.

        If the restriction has a time case, we can't reliably group them into the :conditional tag
        because then we'd have to consolidate these somehow into one tag. That leaves us with e.g.:

            maxheight:destination=none

        However, if there is no time case, we can group the exempting rules into the conditional:

            maxheight=none @ destination;none @ bus
        """
        key = KEY_FROM_TYPE[self.typ]
        exemptor_tags: List[OsmiumTag] = []
        permissive_value = PERMISSIVE_VALUES[self.typ]
        exemptor_modes: List[str] = []
        has_time_case = self.has_time_case()

        for exemptor in self.get_exemptors():
            exemptor_modes.extend(TRAFFIC_MODES[exemptor])

        if (
            has_time_case
            # or self.typ == SEVASRestrType.HGV_NO
            # or (
            #     self.typ == SEVASRestrType.HGV_NO
            #     and ("delivery" not in exemptor_modes and "destination" not in exemptor_modes)
            # )
        ):
            for mode in exemptor_modes:
                # prevent something like hgv:bus=yes, the exemptor in this case would be bus=yes

                if key == SEVASRestrType.HGV_NO:
                    mode_key = mode
                else:
                    mode_key = f"{key}:{mode}"
                exemptor_tags.append(OsmiumTag(mode_key, permissive_value))
        # if there is no time case
        # it makes sense to group the exemptors under the :conditional tag
        # ...unless they're used to specify access for a certain vehicle type
        # like agricultural traffic
        else:
            con_key = f"{key}:conditional"
            rules: List[str] = []
            for mode in exemptor_modes:
                if mode not in NON_KEYABLE and self.typ == SEVASRestrType.HGV_NO:
                    exemptor_tags.append(OsmiumTag(mode, permissive_value))
                else:
                    rules.append(mode)
            if len(rules):
                value = ";".join([f"{permissive_value} @ {rule}" for rule in rules])
                exemptor_tags.append(OsmiumTag(con_key, value))
        return exemptor_tags

    def get_specifier_tags(self) -> List[OsmiumTag]:
        """
        Get the tags based on the restriction's specifiers.
        """
        specifier_tags: List[OsmiumTag] = []
        specifier_modes: List[str] = []
        key = KEY_FROM_TYPE[self.typ]
        times = self._get_time_conditional()
        direction = self._get_direction()
        value = self.wert or "no"

        if has_time_case := self.has_time_case():
            value = f"{value} @ {times}"

        # assemble all the traffic modes from the specifiers
        # (i.e. the ones used to apply the restriction only to certain modes of traffic)
        for specifier in self.get_specifiers():
            specifier_modes.extend(TRAFFIC_MODES[specifier])

        for mode in specifier_modes:
            # to prevent "hgv:another_mode:*"
            if self.typ == SEVASRestrType.HGV_NO:
                mode_key = f"{mode}{direction}"
            else:
                mode_key = f"{key}:{mode}{direction}"

            if has_time_case:
                mode_key = f"{mode_key}:conditional"

            specifier_tags.append(OsmiumTag(mode_key, value))

        return specifier_tags

    def get_special_signature_tags(self) -> List[OsmiumTag]:
        """
        SEVAS restrictions follow a pareto distribution, so we manually handle the 20 or so most common
        ones to make sure over 95% of all restrictions are tagged correctly.

        """
        match sig := self.sign_signature():
            case CommonRestrSignatures.HGV_NO_DEST_ONLY | CommonRestrSignatures.HGV_NO_DELIVERY_ONLY:
                val = "destination" if sig == CommonRestrSignatures.HGV_NO_DEST_ONLY else "delivery"
                if self.has_time_case():
                    return [
                        OsmiumTag("hgv:conditional", f"no @ {self._get_time_conditional()};yes @ {val}")
                    ]
                return [
                    OsmiumTag(f"hgv{self._get_direction()}", "no"),
                    OsmiumTag(f"hgv{self._get_direction()}:conditional", f"yes @ {val}"),
                ]
            case (
                CommonRestrSignatures.HGV_NO_DELIVER_ONLY_7_5T
                | CommonRestrSignatures.HGV_NO_DEST_ONLY_7_5T
            ):
                val = (
                    "destination"
                    if sig == CommonRestrSignatures.HGV_NO_DELIVER_ONLY_7_5T
                    else "delivery"
                )
                if self.has_time_case():
                    return [
                        OsmiumTag(
                            "maxweight:hgv:conditional",
                            f"7.5 @ {self._get_time_conditional()};none @ {val}",
                        )
                    ]
                return [
                    OsmiumTag(f"maxweight{self._get_direction()}", "7.5"),
                    OsmiumTag(f"maxweight{self._get_direction()}:conditional", f"none @ {val}"),
                ]
            case CommonRestrSignatures.HGV_NO_7_5T | CommonRestrSignatures.HGV_NO_12T:
                val = "12" if sig == CommonRestrSignatures.HGV_NO_12T else "7.5"
                if self.has_time_case():
                    return [
                        OsmiumTag(
                            f"maxweight:hgv{self._get_direction()}:conditional",
                            f"{val} @ {self._get_time_conditional()}",
                        )
                    ]
                return [
                    OsmiumTag(f"maxweight:hgv{self._get_direction()}", val),
                ]

        return []

    def get_basic_tag(self) -> List[OsmiumTag]:
        """
        Generates OSM tags based on the record's type, value and temportal restrictions.

        This function is either called when the restriction has no additional signs, or
        when it does but the combination is so weird, there is no point in trying to
        assemble the correct tags for it (should be rare cases only).

        :returns: a list of tags to be passed to Osmium.
        :raises HannibalSchemaError: if a 'wert' attribute is expected but not found
        """

        if not self.is_basic():
            # we are handling a rare fallthrough case
            # TODO: log it
            LOGGER.warn(f"Fallback case for restriction {self.segment_id}")

        key: str = KEY_FROM_TYPE[self.typ]
        value: str = "no"  # default restrictive value

        match self.typ:
            case SEVASRestrType.WEIGHT:
                if not self.wert:
                    raise HannibalSchemaError("wert", str(None), HannibalProvider.SEVAS)
                value = self.reformat_num(self.wert)
            case SEVASRestrType.HEIGHT:
                if not self.wert:
                    raise HannibalSchemaError("wert", str(None), HannibalProvider.SEVAS)
                value = self.reformat_num(self.wert)
            case SEVASRestrType.WIDTH:
                if not self.wert:
                    raise HannibalSchemaError("wert", str(None), HannibalProvider.SEVAS)
                value = self.reformat_num(self.wert)
            case SEVASRestrType.LENGTH:
                if not self.wert:
                    raise HannibalSchemaError("wert", str(None), HannibalProvider.SEVAS)
                value = self.reformat_num(self.wert)

        key = f"{key}{self._get_direction()}"
        conditional = self._get_time_conditional()

        if len(conditional):
            key = f"{key}:conditional"
            value = f"{value} @ {conditional}"

        return OsmiumTag(key, value)

    def _get_direction(self):
        """
        Generate a direction namespace suffix for the OSM tag key.
        """
        match self.fahrtri:
            case SEVASDir.BOTH:
                return ""
            case SEVASDir.FORW:
                return ":forward"
            case SEVASDir.BACKW:
                return ":backward"
            case _:
                raise HannibalSchemaError("fahrtri", str(self.fahrtri), HannibalProvider.SEVAS)

    def _get_time_conditional(self) -> str:
        """
        Generate a temporal restriction value.

        Examples:

        ```
        <tage_einzeln = 1100000>
        "(Mo, Di)"
        ```

        ```
        <tage_einzeln = 0000000>
        ""
        ```

        ```
        <tage_grppe = 1>
        ""
        ```

        ```
        <tage_grppe = 2>
        "(Mo-Fr)"
        ```

        ```
        <tage_grppe = 3>
        "(So, PH)"
        ```

        ```
        <zeit1von = 07:00>
        <zeit1bis = 12:00>
        "07:00-12:00"
        ```

        ```
        <zeit1von = 07:00>
        <zeit1bis = 12:00>
        <zeit2von = 17:00>
        <zeit2bis = 23:00>
        "07:00-12:00,17:00-23:00"
        ```

        ```
        <tage_grppe = 2>
        <zeit1von = 07:00>
        <zeit1bis = 12:00>
        <zeit2von = 17:00>
        <zeit2bis = 23:00>
        "Mo-Fr 07:00-12:00,17:00-23:00"
        ```
        """
        has_single_days = self.tage_einzl != NO_TAGE_EINZL
        has_grouped_days = self.tage_grppe != SEVASGroupedDays.NONE
        has_time = self.zeit1_von != ""

        if not has_single_days and not has_grouped_days and not has_time:
            return ""

        days: str = ""

        if has_single_days:
            if has_grouped_days:
                raise ValueError(
                    f"SEVAS restriction {self.segment_id}: has both single and grouped days."
                )
            if not self.tage_einzl == INVALID_TAGE_EINZL:
                days = ", ".join([DAYS_OF_WEEK[i] for i, v in enumerate(self.tage_einzl) if v == "1"])
        elif has_grouped_days:
            match self.tage_grppe:
                case SEVASGroupedDays.DAILY:
                    pass
                case SEVASGroupedDays.WEEKDAYS:
                    days = "(Mo-Fr)"
                case SEVASGroupedDays.SUNDAYS_HOLIDAYS:
                    days = "(Su,PH)"

        if not has_time:
            return days

        if (self.zeit1_von and not self.zeit1_bis) or (self.zeit2_von and not self.zeit2_bis):
            raise ValueError("SEVAS restriction has start time but no end time")

        times: List[str] = [f"{self.zeit1_von}-{self.zeit1_bis}"]

        if self.zeit2_von:
            times.append(f"{self.zeit2_von}-{self.zeit2_bis}")

        return f"{days}{' ' if len(days) else ''}{','.join(times)}"

    @staticmethod
    def reformat_num(s: str):
        """
        Replaces commas with periods in strings that represent floating point numbers.
        """
        if "," in s:
            return s.replace(",", ".")
        return s


class SEVASRestrictions(ImmutableMixin):
    def __init__(self, dbf_path: Path) -> None:
        """
        SEVAS restriction map. The DBF's records are read into memory at initialization by default.

        :param dbf: path to the restriction PBF file.
        """

        self._dbf_path = dbf_path

        # the mapping default value is an empty list
        self._map: Mapping[int, List[SEVASRestrRecord]] = defaultdict(list)

        dbf = load_dbf(dbf_path, SEVASRestrFactory)

        record: SEVASRestrRecord
        for record in dbf.records:
            self._map[record.osm_id].append(record)

    def __getitem__(self, key: int) -> List[SEVASRestrRecord] | None:
        """
        Access the internal mapping by OSM ID
        """
        return self._map[key] or None

    def items(self) -> Generator[Tuple[int, List[SEVASRestrRecord]], Any, Any]:
        for k, v in self._map.items():
            yield k, v
