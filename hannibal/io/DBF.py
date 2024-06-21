from pathlib import Path
from typing import Callable

from dbfread import DBF

from hannibal.util.exception import HannibalIOError


def load_dbf(p: Path, recfactory: Callable, load: bool = True) -> DBF:
    """
    Load a DBF located at the given path.

    :param p: Path of the DBF file
    :param load: Load records into memory (default) or stream them from file
    :raises HannibalIOError: if anything goes wrong when trying to read the DBF
    """
    try:
        dbf = DBF(p, recfactory=recfactory, lowernames=True, load=load, encoding="utf-8")
    except UnicodeDecodeError:
        dbf = DBF(p, recfactory=recfactory, lowernames=True, load=load, encoding="ISO-8859-1")
    except Exception as e:  # noqa
        raise HannibalIOError(f"Error loading DBF file {p}: {e}")

    return dbf
