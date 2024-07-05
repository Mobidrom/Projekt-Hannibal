import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

from hannibal import PROJECT_NAME


class LogLevel(int, Enum):
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    NOTSET = 0


LOGGER = logging.getLogger("hannibal")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)5s: %(message)s")
handler.setFormatter(formatter)
LOGGER.addHandler(handler)


def init_logger(level: LogLevel, logpath: Path | None = None):
    """simply sets the level on the global logger instance"""
    global LOGGER
    LOGGER.setLevel(level.value)

    if logpath:
        logpath.mkdir(exist_ok=True, parents=True)
        file = (
            logpath
            / f"{datetime.now().isoformat(sep='T', timespec='minutes')}_{PROJECT_NAME.lower()}.txt"
        )
        file_handler = logging.FileHandler(file, mode="w")
        file_handler.setFormatter(formatter)
        LOGGER.addHandler(file_handler)
