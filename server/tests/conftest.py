import pytest
from fastapi.testclient import TestClient

from server import main


@pytest.fixture
def client():
    """A client on a brand-new session with an empty QA log."""
    main.QA_LOG.clear()
    main.SESSIONS.clear()
    return TestClient(main.app)   # a fresh client has no cookie, so it gets its own session


def onboard(client, tier="beginner", symbol="HLX"):
    r = client.post("/api/onboarding", json={"tier": tier, "symbol": symbol})
    assert r.status_code == 200, r.text
    return r.json()["state"]


def order(client, side="BUY", qty=1, symbol="HLX", **extra):
    cursor = client.get("/api/state").json()["cursor"]
    return client.post("/api/orders", json={"symbol": symbol, "side": side, "qty": qty, "as_of": cursor, **extra})
