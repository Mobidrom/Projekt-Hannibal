from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Self, Type

from hannibal.io.YAML import load_yaml
from hannibal.providers import HannibalProvider


@dataclass
class ProviderBaseConfig:
    clean: bool
    clean_tags: List[str] | None
    relation: int | None


@dataclass
class OsmBaseConfig:
    """Configure the OSM input."""

    path: Path | None
    url: str | None


@dataclass
class OutputConfig:
    """Configure the output."""

    path: Path


@dataclass
class HannibalConfig:
    """Class that holds the global configuration in memory"""

    providers: Mapping[HannibalProvider, ProviderBaseConfig]
    osm_base: OsmBaseConfig
    output: OutputConfig

    @classmethod
    def from_path(cls, p: Path) -> Type[Self]:
        conf = load_yaml(p)
        providers: Mapping[HannibalProvider, ProviderBaseConfig] = {}

        try:
            for prov, prov_dict in conf["providers"].items():
                provider_conf = ProviderBaseConfig(
                    prov_dict.get("cleanTags", {}).get("active") or False,
                    prov_dict.get("cleanTags", {}).get("tags"),
                    prov_dict.get("cleanTags", {}).get("area"),
                )
                providers[HannibalProvider(prov.lower())] = provider_conf

            osm_base_dict = conf["osmBase"]
            osm_base_conf = OsmBaseConfig(osm_base_dict.get("path"), osm_base_dict.get("url"))

            output_config = OutputConfig(conf["output"]["path"])

            return cls(providers, osm_base_conf, output_config)

        except Exception as e:  # noqa
            raise ValueError(f"Error loading config from file: {e}")
