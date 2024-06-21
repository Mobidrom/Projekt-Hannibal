from pathlib import Path
from typing import Mapping

from yaml import safe_load


def load_yaml(path: Path) -> Mapping:
    with open(path, "r") as fh:
        yaml = safe_load(fh)
        return yaml
