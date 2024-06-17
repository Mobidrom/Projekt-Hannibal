from enum import Enum

NO_TAGE_EINZL = "0" * 7
INVALID_TAGE_EINZL = "1" * 7
DAYS_OF_WEEK = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


class RestrVZ(str, Enum):
    # specifier HGV
    VZ_1010_51 = "vz_1010_51"
    # specifier bus
    VZ_1010_57 = "vz_1010_57"
    # specifier HGV with trailer
    VZ_1010_60 = "vz_1010_60"
    # exemptor destination
    VZ_1020_30 = "vz_1020_30"
    # exemptor HGV
    VZ_1024_12 = "vz_1024_12"
    # exemptor HGV with trailer
    VZ_1024_13 = "vz_1024_13"
    # exemptor bus
    VZ_1024_14 = "vz_1024_14"
    # exemptor tourist bus
    VZ_1026_31 = "vz_1026_31"
    # exemptor psv
    VZ_1026_32 = "vz_1026_32"
    # exemptor emergency
    VZ_1026_33 = "vz_1026_33"
    # exemptor ambulance/emergency
    VZ_1026_34 = "vz_1026_34"
    # exemptor delivery
    VZ_1026_35 = "vz_1026_35"
    # exemptor agriculture
    VZ_1026_36 = "vz_1026_36"
    # exemptor forestry
    VZ_1026_37 = "vz_1026_37"
    # exemptor agriculture and forestry
    VZ_1026_38 = "vz_1026_38"
    # exemptor police/military/etc. (handle as special case)
    VZ_1026_39 = "vz_1026_39"
    # exemptor slurry tank (treat as agricultural)
    VZ_1026_62 = "vz_1026_62"
    # specifier articulated HGV
    VZ_1048_14 = "vz_1048_14"
    # specifier articulated HGV or HGV with trailer (handle as special case)
    VZ_1048_15 = "vz_1048_15"
    # specifier HGV, bus and auto with trailer (handle as special case)
    VZ_1049_13 = "vz_1049_13"
    # specifier 7.5t (special case)
    VZ_1053_33 = "vz_1053_33"
    # specifier through traffic (treat as destination only)
    VZ_1053_36 = "vz_1053_36"
    # specifier 12t (special case)
    VZ_1053_37 = "vz_1053_37"


class SEVASRestrType(str, Enum):
    HGV_NO = "253"
    HGV_TRAILER = "257-57"
    HAZMAT = "261"
    WEIGHT = "262"
    AXLE_LOAD = "263"
    WIDTH = "264"
    HEIGHT = "265"
    LENGTH = "266"
    HAZMAT_WATER = "269"


TRAFFIC_MODES = {
    RestrVZ.VZ_1010_51: ["hgv"],
    RestrVZ.VZ_1010_57: ["bus"],
    RestrVZ.VZ_1010_60: ["hgv:trailer"],
    RestrVZ.VZ_1020_30: ["destination"],
    RestrVZ.VZ_1024_12: ["hgv"],
    RestrVZ.VZ_1024_13: ["hgv", "trailer"],
    RestrVZ.VZ_1024_14: ["bus"],
    RestrVZ.VZ_1026_31: ["tourist_bus"],
    RestrVZ.VZ_1026_32: ["psv"],
    RestrVZ.VZ_1026_33: ["emergency"],
    RestrVZ.VZ_1026_34: ["emergency"],
    RestrVZ.VZ_1026_35: ["delivery"],
    RestrVZ.VZ_1026_36: ["agricultural"],
    RestrVZ.VZ_1026_37: ["forestry"],
    RestrVZ.VZ_1026_38: ["agricultural", "forestry"],
    RestrVZ.VZ_1026_39: ["private", "delivery"],
    RestrVZ.VZ_1026_62: ["agricultural"],
    RestrVZ.VZ_1048_14: ["articulated_hgv"],
    RestrVZ.VZ_1053_36: ["destination"],
}

# as opposed to other traffic modes,
# these can not be used as keys in OSM
NON_KEYABLE = [
    "destination",
    "delivery",
]

DIMENSIONAL_RESTRICTION_TYPES = [
    SEVASRestrType.AXLE_LOAD,
    SEVASRestrType.WEIGHT,
    SEVASRestrType.HEIGHT,
    SEVASRestrType.WIDTH,
    SEVASRestrType.LENGTH,
]


# signatures of the most common restrictions
# commented out the ones that are tagged well
# already
class CommonRestrSignatures(str, Enum):
    HGV_NO_DEST_ONLY = "25300010000000000000000000"
    # HGV_NO = "25300000000000000000000000"
    HGV_NO_DELIVERY_ONLY = "25300000000000100000000000"
    # MAXWEIGHT = "26200000000000000000000000"
    # MAXHEIGHT = "26500000000000000000000000"
    # MAXWEIGHT_DEST_ONLY = "26200010000000000000000000"
    HGV_NO_DELIVER_ONLY_7_5T = "25300000000000100000000100"
    # MAXLENGTH = "26600000000000000000000000"
    # HAZMAT = "26100000000000000000000000"
    HGV_NO_7_5T = "25300000000000000000000100"
    HGV_NO_DEST_ONLY_7_5T = "25300010000000000000000100"
    # HAZMAT_WATER = "26900000000000000000000000"
    # MAXWEIGHT_BUS_EXEMPT = "26200000010000000000000000"
    # MAXWIDTH = "26400000000000000000000000"
    HGV_NO_12T = "25300000000000000000000001"
    MAXWEIGHT_DELIVERY_ONLY = "26200000000000100000000000"
    # HGV_NO_NO_THRU = "25300000000000000000000010"
    HGV_NO_DEST_DELIVERY = "25300010000000100000000000"
    # HGV_NO_AGRICULTURAL_YES = "25300000000000010000000000"
    # HGV_NO_BUS_YES = "25300000010000000000000000"
    # AXLE_LOAD = "26300000000000000000000000"
    # MAXWEIGHT_DELIVERY_DEST = "26200010000100000000000000"
    # HGV_NO_FORESTRY_AGRICULTURAL_EXEMPT = "25300000000000000100000000"


PERMISSIVE_VALUES = {
    SEVASRestrType.HGV_NO: "yes",
    SEVASRestrType.HGV_TRAILER: "yes",
    SEVASRestrType.HAZMAT: "yes",
    SEVASRestrType.WEIGHT: "none",
    SEVASRestrType.AXLE_LOAD: "none",
    SEVASRestrType.WIDTH: "none",
    SEVASRestrType.HEIGHT: "none",
    SEVASRestrType.LENGTH: "none",
    SEVASRestrType.HAZMAT_WATER: "yes",
}

# these can be combined with each other pretty much
# any way
EXEMPTORS = [
    RestrVZ.VZ_1020_30,
    RestrVZ.VZ_1024_12,
    RestrVZ.VZ_1024_13,
    RestrVZ.VZ_1024_14,
    RestrVZ.VZ_1026_31,
    RestrVZ.VZ_1026_32,
    RestrVZ.VZ_1026_33,
    RestrVZ.VZ_1026_34,
    RestrVZ.VZ_1026_35,
    RestrVZ.VZ_1026_36,
    RestrVZ.VZ_1026_37,
    RestrVZ.VZ_1026_38,
    RestrVZ.VZ_1026_39,
    RestrVZ.VZ_1026_62,
    RestrVZ.VZ_1053_36,
]


# one at a time only please
SPECIFIERS = [
    RestrVZ.VZ_1010_51,
    RestrVZ.VZ_1010_57,
    RestrVZ.VZ_1010_60,
    RestrVZ.VZ_1048_14,
]

# handle individually
SPECIAL_VZ = [
    RestrVZ.VZ_1026_39,
    RestrVZ.VZ_1048_15,
    RestrVZ.VZ_1049_13,
    RestrVZ.VZ_1053_33,
    RestrVZ.VZ_1053_37,
]
