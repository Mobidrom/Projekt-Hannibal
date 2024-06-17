from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    key: str
    value: str
