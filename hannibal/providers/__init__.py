from enum import Enum


class HannibalProvider(str, Enum):
    SEVAS = "sevas"
    TOMTOM = "tomtom"
    HERE = "here"
