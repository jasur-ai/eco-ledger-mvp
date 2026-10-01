# -*- coding: utf-8 -*-
"""Adolat paketi testlari — tushuntirish kartasi (1C §C.2) va aniqlik hisoboti (§E.2)."""
import os
import sys

ADS_DB = "/tmp/eco_ledger_adolat.db"
os.environ["ECO_LEDGER_DB"] = ADS_DB
if os.path.exists(ADS_DB):
    os.remove(ADS_DB)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest                                            # noqa: E402
from src import adolat, config, db                       # noqa: E402
from src.seed import seed                                # noqa: E402

_conn = db.connect(ADS_DB)
if _conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0:
    seed(_conn)

from fastapi.testclient import TestClient                # noqa: E402
from src.api.app import app                              # noqa: E402


@pytest.fixture()
def conn():
    return db.connect(ADS_DB)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", ADS_DB)
    return TestClient(app)


# ------------------------------------------------------------------ karta (12 maydon)

def test_card_has_12_fields(conn):
    card = adolat.explain_card(conn, "E-1001")
    assert card["maydonlar_soni"] == adolat.KARTA_MAJBURIY == 12
    assert len(card["kartochka"]) == 12
    for i in range(1, 13):
        assert any(k.startswith(f"{i}_") for k in card["kartochka"]), f"{i}-maydon yo'q"


def test_card_filled_fields_are_real(conn):
    card = adolat.explain_card(conn, "E-1001")["kartochka"]
    assert card["3_qiymat"]["holat"] == "bor" and "µg/m³" in card["3_qiymat"]["qiymat"]
    assert "R=" in card["6_qaror_qoidasi"]["qiymat"] and card["6_qaror_qoidasi"]["sabablar"]


def test_card_missing_data_is_disclosed_not_hidden(conn):
    """1C talabi: yo'q ma'lumot «0» emas, «mavjud emas» + sabab bo'lishi kerak."""
    card = adolat.explain_card(conn, "E-1001")["kartochka"]
    u = card["4_noaniqlik_U"]
    assert u["holat"] == "mavjud emas" and u["qiymat"] is None and "TZ-1" in u["sabab"]
    k = card["9_koeffitsient"]
    assert k["holat"] == "qo'llanilmaydi" and "jarima" in k["sabab"]


def test_card_three_questions_answered(conn):
    card = adolat.explain_card(conn, "E-1001")
    t = card["uch_savol"]
    assert t["nima_olchandi"] and "217" in t["nima_olchandi"]
    assert "6.20" in t["nega_shunday_qaror"] and "Qizil" in t["nega_shunday_qaror"]
    assert "10 kun" in t["qanday_etiroz"] and "30 ish kuni" in t["qanday_etiroz"]


def test_card_unknown_facility(conn):
    with pytest.raises(ValueError):
        adolat.explain_card(conn, "E-9999")


# ------------------------------------------------------------------ e'tiroz matni

def test_objection_text_uz_and_ru(conn):
    card = adolat.explain_card(conn, "E-1001")
    uz, ru = adolat.objection_text(card, "uz"), adolat.objection_text(card, "ru")
    assert "E'TIROZ" in uz and "1) Nima o'lchandi" in uz and "append-only" in uz
    assert "ОБЖАЛОВАНИЕ" in ru and "Что измерено" in ru
    assert card["eco_id"] in uz and card["eco_id"] in ru


# ------------------------------------------------------------------ aniqlik hisoboti

def test_report_has_5_metrics(conn):
    rep = adolat.accuracy_report(conn)
    assert len(rep["metrikalar"]) == 5
    assert [m["nomi"][:12] for m in rep["metrikalar"]][0] == "Signallar so"


def test_report_counts_match_zone_data(conn):
    rep = adolat.accuracy_report(conn)["metrikalar"]
    n_red = conn.execute("SELECT COUNT(*) FROM facility_classes WHERE zone_class='red' "
                         "AND id IN (SELECT MAX(id) FROM facility_classes GROUP BY eco_id)").fetchone()[0]
    n_yellow = conn.execute("SELECT COUNT(*) FROM facility_classes WHERE zone_class='yellow' "
                            "AND id IN (SELECT MAX(id) FROM facility_classes GROUP BY eco_id)").fetchone()[0]
    assert rep[0]["qiymat"] == n_red + n_yellow
    assert rep[1]["qiymat"] == pytest.approx(n_yellow / (n_red + n_yellow), abs=1e-4)


def test_report_undefined_metrics_have_reason(conn):
    rep = adolat.accuracy_report(conn)["metrikalar"]
    for idx in (2, 4):                                   # precision va U/L
        m = rep[idx]
        assert m["qiymat"] is None and m["holat"] == "mavjud emas" and m["sabab"]


def test_report_disclosure_rule(conn):
    rep = adolat.accuracy_report(conn)
    assert "JUFTLIKDA" in rep["oskorlik_qoidasi"] or "juftlikda" in rep["oskorlik_qoidasi"]
    assert "nol bilan yashirilmaydi" in rep["oskorlik_qoidasi"]


# ------------------------------------------------------------------ apellyatsiya oynasi

def test_appeal_window_is_30_workdays():
    w = adolat.appeal_window("2026-09-25")               # juma
    assert w["javob_muddati"] == "2026-10-05"
    from datetime import date
    d0, d1 = date.fromisoformat(w["qaror_sanasi"]), date.fromisoformat(w["apellyatsiya_oxiri"])
    assert round((d1 - d0).days * 5 / 7) >= 20           # ~30 ish kuni ≈ 42 kalendar kun
    assert 40 <= (d1 - d0).days <= 46


def test_appeal_window_weekend_start():
    w = adolat.appeal_window("2026-09-26")               # shanba — hisob shanbadan boshlanadi
    assert w["apellyatsiya_oxiri"] > w["qaror_sanasi"]


# ------------------------------------------------------------------ API

def test_api_karta_endpoint(client):
    r = client.get("/v1/adolat/karta/E-1001")
    assert r.status_code == 200
    body = r.json()
    assert body["maydonlar_soni"] == 12 and set(body["etiroz_matni"]) == {"uz", "ru"}


def test_api_hisobot_endpoint(client):
    r = client.get("/v1/adolat/hisobot")
    assert r.status_code == 200 and len(r.json()["metrikalar"]) == 5


def test_api_oyna_endpoint(client):
    assert client.get("/v1/adolat/oyna?qaror_sanasi=2026-09-25").status_code == 200
    assert client.get("/v1/adolat/oyna?qaror_sanasi=xato").status_code == 400


def test_api_karta_404(client):
    assert client.get("/v1/adolat/karta/E-9999").status_code == 404
