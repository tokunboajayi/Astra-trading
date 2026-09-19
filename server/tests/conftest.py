import pytest
from fastapi.testclient import TestClient

from server import main


@pytest.fixture
def client():
    """A client on a brand-new session with an empty QA log."""
    main.QA_LOG.clear()
    main.SESSIONS.clear()
    return TestClient(main.app)   # a fresh client has no cookie, so it gets its own session


def onboard(client, experience="new", symbol="HLX"):
    r = client.post("/api/onboarding", json={"experience": experience, "symbol": symbol})
    assert r.status_code == 200, r.text
    return r.json()["state"]


def order(client, side="BUY", qty=10, **extra):
    cursor = client.get("/api/state").json()["cursor"]
    return client.post("/api/orders", json={"symbol": "HLX", "side": side, "qty": qty, "as_of": cursor, **extra})
