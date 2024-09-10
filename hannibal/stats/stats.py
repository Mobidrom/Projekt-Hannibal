from enum import Enum


class StatsCategory(str, Enum):
    # tag related: counts kept per tag key
    ADDED = "added"  # a new tag is added
    OVERRIDDEN = "overridden"  # a tag is overridden
    REMOVED = "removed"

    # geometry related: simple count of how many ways were split
    SPLIT = "split"
