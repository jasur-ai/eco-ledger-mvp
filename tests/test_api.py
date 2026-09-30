# -*- coding: utf-8 -*-
"""S1/S3 — API testlari (ochiq endpointlar, o'chirish yo'qligi)."""
import os
import sys

API_DB = "/tmp/eco_ledger_test.db"                      # faqat shu modul bazasi
os.environ["ECO_LEDGER_DB"] = API_DB
if os.path.exists(API_DB):
    os.remove(API_DB)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest                                         # noqa: E402
from src import config, db                            # noqa: E402
from src.seed import seed                             # noqa: E402

_conn = db.connect(API_DB)                            # yo'l aniq beriladi — global holat yo'q
if _conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0:
    seed(_conn)
_conn.close()

from fastapi.testclient import TestClient             # noqa: E402
from src.api.app import app                           # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    """config.DB_PATH har testda shu modul bazasiga o'rnatiladi (testdan keyin tiklanadi)."""
    monkeypatch.setattr(config, "DB_PATH", API_DB)
    return TestClient(app)


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["facilities"] > 30


def test_zones_geojson(client):
    r = client.get("/v1/geo/zones.geojson")
    assert r.status_code == 200
    d = r.json()
    assert len(d["features"]) == 6
    for f in d["features"]:
        assert f["properties"]["zone_color"] in ("red", "yellow", "green", "blue")
        assert "coverage" in f["properties"]


def test_measurements_csv(client):
    r = client.get("/v1/export/measurements.csv")
    assert r.status_code == 200
    assert "eco_id" in r.text.splitlines()[0]


def test_facility_card_and_badges(client):
    r = client.get("/v1/facilities/E-1001")
    assert r.status_code == 200
    d = r.json()
    assert d["class"]["zone_class"] == "red"
    assert d["badges"] and d["badges"][0]["ratio"] > 5      # JSST yorlig'i


def test_appeal_flow_via_api(client):
    body = {"description": "Sergeli tumanida yo'lda chang ko'tarilmoqda, yuk mashinalari sabab.",
            "category": "air", "lat": 41.22, "lon": 69.22, "phone": "+998971234567"}
    r = client.post("/v1/appeals", json=body)
    assert r.status_code == 200
    code = r.json()["public_code"]
    r2 = client.post(f"/v1/appeals/{code}/transitions",
                     json={"to_status": "ko'rib_chiqilmoqda", "actor": "system"})
    assert r2.status_code == 200 and r2.json()["status"] == "ko'rib_chiqilmoqda"
    # noto'g'ri o'tish
    r3 = client.post(f"/v1/appeals/{code}/transitions",
                     json={"to_status": "hal_qilindi", "actor": "operator"})
    assert r3.status_code == 400


def test_no_delete_endpoint(client):
    r = client.delete("/v1/appeals/A-2026-000001")
    assert r.status_code in (404, 405)      # o'chirish yo'q


def test_kpi_sla(client):
    r = client.get("/v1/kpi/sla")
    assert r.status_code == 200 and "compliance_pct" in r.json()


def test_bot_summary_passes_verification(client):
    r = client.get("/v1/bot/summary")
    assert r.status_code == 200
    d = r.json()
    assert d["verify_status"] == "PASS" and d["format"] == "bot"
