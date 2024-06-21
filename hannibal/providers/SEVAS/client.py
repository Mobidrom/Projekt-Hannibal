from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

import requests

from hannibal.logging import LOGGER
from hannibal.providers.SEVAS.constants import SEVASLayer
from hannibal.util.exception import HannibalIOError


class SEVASClient:
    def __init__(
        self,
        data_dir: Path,
        base_url: str,
        version: str = "2.0.0",
        unzip: bool = True,
        test: bool = False,
    ) -> None:
        """
        SEVAS WFS client to access SEVAS data via the WFS API.

        :param data_dir: directory to which the SEVAS data will be saved
        :param base_url: base URL of the SEVAS Web Feature Service
        :param version: WFS version
        :param unzip: whether to unzip the downloaded zip files
        :param test: when in test mode, only download 1 feature per layer
        """

        self._data_dir = data_dir
        self._base_url = base_url
        self._version = version
        self._test = test

        # create additional zip directory
        self._zip_dir = self._data_dir / "zip"
        self._zip_dir.mkdir(exist_ok=True, parents=False)

    def get_all(self):
        """
        Convenience method to download all SEVAS data.
        """

        for layer in SEVASLayer:
            self.get(layer)

        self.clean()

    def clean(self):
        """
        Clean up any temporary files.
        """
        zip_is_empty = not any(self._zip_dir.iterdir())

        if zip_is_empty:
            self._zip_dir.rmdir()

    def get(self, layer: SEVASLayer, unzip: bool = True):
        """
        Download SEVAS data as a zipped directory for a given layer to the
        clients data directory and optionally unzip it.
        """
        filter = self._get_filter(layer)
        url = (
            f"{self._base_url}?SERVICE=WFS"
            + f"&VERSION={self._version}&REQUEST=getfeature&TYPENAME={layer.value}"
            + f"{filter}&OUTPUTFORMAT=ShapeZip{self._get_max_feature_filter()}"
        )
        fp = self.get_zip_file_path(layer)
        LOGGER.info(url)

        LOGGER.info(f"Downloading SEVAS layer for {layer.value}, saving to {fp}")

        r = requests.get(url, stream=True)
        if not r.ok:
            raise HannibalIOError(f"Failed to download SEVAS data from {url}")
        with open(fp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)

        if unzip:
            LOGGER.info(f"Unzipping {fp} to  {self._data_dir}")
            self._unzip(
                fp,
                layer in [SEVASLayer.ROAD_SPEEDS, SEVASLayer.PREFERRED_ROADS, SEVASLayer.RESTRICTIONS],
            )

    def get_zip_file_path(self, layer: SEVASLayer) -> Path:
        """
        Gets full path for storing a layer zip file.
        """

        return self._zip_dir / (layer.value + ".zip")

    def _unzip(self, fp: Path, only_dbf: bool = False, keep_zip: bool = False) -> None:
        """
        Unzips zipped files into the data directory

        :param fp: path to the zipfile
        :param only dbf: only extract the DBF file
        """

        if not only_dbf:
            with ZipFile(fp, "r") as zf:
                zf.extractall(self._data_dir)
        else:
            with ZipFile(fp, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".dbf"):
                        zf.extract(name, self._data_dir)

        if not keep_zip:
            fp.unlink()

    def _get_max_feature_filter(self) -> str:
        """
        Only download 1 feature per layer when in test mode, only used for testing.
        """

        return "" if not self._test else "&MAXFEATURES=1"

    @staticmethod
    def _get_filter(layer: SEVASLayer) -> str:
        """
        We can filter out some features for some layers.
          1. we only need the low emission zone polygons
          2. we only need the speed polygon segments

        :param layer: the requested layer
        :return: the filter string
        """

        filter = (
            """
        &Filter=<Filter>
                    <PropertyIsEqualTo
                        <PropertyName>
                            typ
                        </PropertyName>
                        <Literal>
                            $$typ$$
                        </Literal>
                    <PropertyIsEqualTo>
                </Filter>
                """.replace("\n", "")
            .replace("\t", "")
            .replace(" ", "")
        )

        match layer:
            case SEVASLayer.LOW_EMISSION_ZONES:
                return escape(filter.replace("$$typ$$", "umweltzone"))
            case SEVASLayer.ROAD_SPEEDS:
                return escape(filter.replace("$$typ$$", "tempozone"))
            case _:
                return ""
