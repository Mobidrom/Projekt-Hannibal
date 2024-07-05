from pathlib import Path

import pytest

from hannibal import ROOT_DIR
from hannibal.providers.SEVAS.client import SEVASClient


@pytest.fixture()
def path():
    test_path = Path(ROOT_DIR) / "data/sevas_client_test"
    test_path.mkdir(parents=True, exist_ok=False)

    yield test_path

    # clean up
    for f in test_path.glob("*"):
        f.unlink()

    test_path.rmdir()


def test_client(path: Path):
    """
    Tests the SEVAS client. In test mode, only one feature per layer is downloaded.
    """
    path = Path(ROOT_DIR) / "data/sevas_client_test"

    c = SEVASClient(path, "https://sevas.nrw.de/osm/sevas", test=True)
    c.get_all()
    assert len([f for f in path.glob("*")]) == 20
