import subprocess

from hannibal import ROOT_DIR
from hannibal.logging import LOGGER


def get_git_current_head_rev() -> str:
    """
    Returns the current head revision hash. Warns the user if git could not be found,
    the working directory is dirty, or the revision hash could not be determined for another reason.
    """
    try:
        subprocess.check_output(["git", "-C", ROOT_DIR, "diff-index", "--quiet", "HEAD"])
    except FileNotFoundError:
        LOGGER.error(
            "git command could not be found. "
            "Output files written cannot be correlated to specific prop2osm version."
        )
    except subprocess.CalledProcessError:
        LOGGER.warning(
            "Dirty working tree detected."
            "Output files written cannot be correlated to specific prop2osm version."
        )

    try:
        return (
            subprocess.check_output(["git", "-C", ROOT_DIR, "rev-parse", "--short", "HEAD"])
            .decode("ascii")
            .strip()
        )
    except subprocess.CalledProcessError:
        LOGGER.error(
            "Git revision of HEAD could not be determined. "
            "Output files written cannot be correlated to specific prop2osm version."
        )

    return "unknown-git-hash"
