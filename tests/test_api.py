"""End-to-end API tests. Uses SQLite so they run without Postgres (run: pytest -q)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'data' / 'test.db'}"
os.environ["MAX_FRAMES"] = "30"

import pytest
from fastapi.testclient import TestClient

from backend.app.database import Base, engine
from backend.app.main import app

SAMPLE = ROOT / "data" / "sample"


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/auth/register", json={"email": "planner@city.gov", "password": "secret123", "full_name": "Planner"})
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", data={"username": "planner@city.gov", "password": "secret123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_requires_auth(client):
    assert client.get("/api/analyses").status_code == 401


def _upload(client, auth, name, location, lat, lon):
    with (SAMPLE / name).open("rb") as fh:
        r = client.post("/api/analyze", headers=auth, data={"location": location, "latitude": lat, "longitude": lon},
                        files={"file": (name, fh, "video/mp4")})
    assert r.status_code == 201, r.text
    return r.json()


def test_analyze_light_and_heavy(client, auth):
    light = _upload(client, auth, "light_traffic.mp4", "Jubilee Hills Rd 36", 17.43, 78.41)
    heavy = _upload(client, auth, "heavy_traffic.mp4", "Hitec City Jn", 17.45, 78.38)
    for a in (light, heavy):
        assert a["status"] == "done", a["error"]
        assert a["congestion_level"] in ("Low", "Moderate", "High")
        assert a["co2_kg_per_hour"] >= 0
        assert "emissions" in a["details"]
        eco = a["details"]["sustainability"]
        assert eco["status"] in ("Eco-Friendly", "Near Limit", "Over Limit")
        assert isinstance(eco["within_limit"], bool)
        assert eco["carbon_limit_kg_per_hour"] == 2500.0
    assert heavy["avg_vehicles"] > light["avg_vehicles"]
    assert heavy["co2_kg_per_hour"] > light["co2_kg_per_hour"]


def test_reject_bad_extension(client, auth):
    r = client.post("/api/analyze", headers=auth, data={"location": "x"}, files={"file": ("a.txt", b"hi", "text/plain")})
    assert r.status_code == 400


def test_list_summary_hotspots_forecast(client, auth):
    rows = client.get("/api/analyses", headers=auth).json()
    assert len(rows) == 2
    s = client.get("/api/summary", headers=auth).json()
    assert s["total_analyses"] == 2 and s["locations"] == 2
    assert s["carbon_limit_kg_per_hour"] == 2500.0
    assert s["within_limit"] + s["over_limit"] == 2
    assert 0 <= s["pct_within_limit"] <= 100
    hs = client.get("/api/hotspots", headers=auth).json()
    assert hs[0]["rank"] == 1 and hs[0]["location"] == "Hitec City Jn"
    fc = client.get("/api/forecast", headers=auth, params={"location": "Hitec City Jn", "horizon_hours": 3}).json()
    assert len(fc) == 3 and fc[0]["level"] in ("Low", "Moderate", "High")


def test_model_info_before_after(client, auth):
    info = client.get("/api/model/info", headers=auth).json()
    if not info.get("trained"):
        pytest.skip("model not trained in this environment")
    # XGBoost metrics must expose accuracy, precision, recall and F1
    assert set(info["metrics"]) >= {"accuracy", "precision_macro", "recall_macro", "f1_macro"}
    for k in ("accuracy", "precision_macro", "recall_macro", "f1_macro"):
        assert 0.0 <= info["metrics"][k] <= 1.0
    cmp = info["comparison"]
    assert set(cmp["before"]) >= {"accuracy", "f1_macro"}
    assert set(cmp["after"]) >= {"accuracy", "f1_macro"}
    # XGBoost should beat the naive count rule on the test split
    assert cmp["after"]["accuracy"] >= cmp["before"]["accuracy"]


def test_sustainability_bands():
    from ml.sustainability import assess_sustainability
    assert assess_sustainability(1000, 2500)["status"] == "Eco-Friendly"   # <= 80% of limit
    assert assess_sustainability(2200, 2500)["status"] == "Near Limit"      # 80-100%
    over = assess_sustainability(3000, 2500)
    assert over["status"] == "Over Limit" and over["within_limit"] is False
    assert over["margin_kg_per_hour"] == -500.0


def test_delete(client, auth):
    rows = client.get("/api/analyses", headers=auth).json()
    assert client.delete(f"/api/analyses/{rows[0]['id']}", headers=auth).status_code == 204
    assert len(client.get("/api/analyses", headers=auth).json()) == 1
