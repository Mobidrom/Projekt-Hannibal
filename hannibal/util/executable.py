from shutil import which


def find_osmium() -> bool:
    return which("osmium")
