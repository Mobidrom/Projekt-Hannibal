from pathlib import Path

from hannibal.providers.SEVAS.client import SEVASClient


def test_client():
    """
    Tests the SEVAS client. In test mode, only one feature per layer is downloaded.
    """
    test_path = Path("data/sevas_client_test")
    test_path.mkdir(exist_ok=False)

    c = SEVASClient(test_path, "https://sevas.nrw.de/osm/sevas", test=True)
    c.get_all()
    assert len([f for f in test_path.glob("*")]) == 11

    # clean up
    for f in test_path.glob("*"):
        f.unlink()

    test_path.rmdir()
