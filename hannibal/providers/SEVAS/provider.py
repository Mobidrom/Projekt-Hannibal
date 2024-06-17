from pathlib import Path

from hannibal.io.OSM import OSMRewriter
from hannibal.providers.SEVAS.tables.restrictions import SEVASRestrictions


class SEVASProvider:
    def __init__(
        self,
        in_path: Path,
        out_path: Path,
        polygons_path: Path,
        polygons_segments_path: Path,
        restrctions_path: Path,
        signs_path: Path,
    ) -> None:
        """
        Provider class that handles the SEVAS conversion.

        :param in_path: Path to base OSM file. Contents will not be altered.
        :param out_path: Path to the resulting OSM file. Contains contents from base OSM file,
                         with changes based on SEVAS data.
        :param polygons_path: Path to SEVAS polygons file.
        :param polygons_segments_path: Path to SEVAS polygon segments file.
        :param restrictions_path: Path to SEVAS restrictions file.
        :param signs_path: Path to SEVAS signs file.
        """

        self._in_path = in_path
        self._out_path = out_path
        self._polygons_path = polygons_path
        self._polygons_segments_path = polygons_segments_path
        self._restrictions_path = restrctions_path
        self._signs_path = signs_path

        # create mappings OSM_ID -> [*sevas_records]
        restrictions = SEVASRestrictions(self._restrictions_path)

        self._rewriter: OSMRewriter = OSMRewriter(in_path, out_path, restrictions)

    def process(self):
        """
        Starts the actual conversion process by applying the base OSM file to the rewriter
        """
        self._rewriter.apply_file(self._in_path)
        self._rewriter.close()

    @property
    def restrictions(self):
        return self._rewriter._restrictions
