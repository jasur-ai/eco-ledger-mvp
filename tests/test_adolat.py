# -*- coding: utf-8 -*-
"""Adolat paketi testlari — tushuntirish kartasi (1C §C.2) va aniqlik hisoboti (§E.2)."""
import os
import sys

ADS_DB = "/tmp/eco_ledger_adolat.db"
os.environ["ECO_LEDGER_DB"] = ADS_DB
if os.path.exists(ADS_DB):
    os.remove(ADS_DB)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re

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


# ------------------------------------------------------------------ chop etiladigan karta (R41)

def test_card_html_has_required_parts(conn):
    html = adolat.card_html(conn, "E-1001")
    assert html.startswith("<!DOCTYPE html>") and "A4" in html
    for i in range(1, 13):                                  # 12 maydon raqami ko'rinadi
        assert f">{i}</td>" in html
    assert "Nima o'lchandi" in html and "Nega shunday qaror" in html and "Qanday e'tiroz" in html
    # R58: kartadagi arifmetika o'z-o'ziga mos bo'lishi shart (har obyekt uchun)
    for eco in ("E-1001", "E-1003", "E-1005"):
        h = adolat.card_html(conn, eco)
        izoh = re.search(r"2\) Nega shunday qaror: ([^<\n]*)", h).group(1)
        kasr = re.search(r"R = ([\d.]+)/([\d.]+) = ([\d.]+)", izoh)
        if kasr:
            a_, b_, c_ = (float(x) for x in kasr.groups())
            assert abs(a_ / b_ - c_) <= 0.02, f"{eco}: ziddiyatli arifmetika → {izoh}"
        assert "None" not in izoh and "?" not in izoh, f"{eco}: to'ldirilmagan maydon → {izoh}"
        # qizil, lekin R < 2,0 bo'lsa — asosiy shart emas, qo'llanilgan qoida ko'rsatilishi kerak
        if izoh.startswith("R =") and "Qizil" in izoh:
            r_qiymat = float(re.search(r"= ([\d.]+) →", izoh).group(1))
            if r_qiymat < 2.0:
                assert "qo'llanilgan qoida" in izoh, f"{eco}: ziddiyatli izoh → {izoh}"
    assert "ОБЖАЛОВАНИЕ" in html                            # ruscha matn ham bor
    assert "<svg" in html                                   # QR kod ichida (tashqi resurs yo'q)
    assert "append-only" in html
    # R58: sabablar ro'yxati harfma-harf chiqmasligi shart (har <li> — to'liq jumla)
    li = re.findall(r"<li>(.*?)</li>", html)
    assert li, "qaror sabablari ro'yxati yo'q"
    assert all(len(x) > 5 for x in li), f"harfma-harf chiqish: {li[:6]}"
    # R58: qaror izohi qo'llanilgan qoidaga mos bo'lishi shart (override bo'lsa — override)
    card = adolat.explain_card(conn, "E-1001")
    nega = card["uch_savol"]["nega_shunday_qaror"]
    if card["kartochka"]["6_qaror_qoidasi"]["qiymat"].startswith("zona: Qizil") and "R=" in nega:
        r_qiymat = float(nega.split("R = ")[1].split(" = ")[1].split(" →")[0])
        if r_qiymat < 2.0:
            assert "qo'llanilgan qoida" in nega, f"ziddiyatli izoh: {nega}"


def test_card_html_no_external_resources(conn):
    html = adolat.card_html(conn, "E-1001")
    # tashqi <script>/<link>/<img src> bo'lmasligi kerak (faqat inline SVG QR)
    assert "<script" not in html and "<link" not in html
    assert 'src="http' not in html


def test_card_pdf_is_single_page(conn, tmp_path):
    fpdf = pytest.importorskip("fpdf")                        # muhitda bo'lmasa — o'tkazib yuboriladi
    import re
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    import build_card as bc
    out = str(tmp_path / "karta.pdf")
    assert bc.build_pdf(conn, "E-1001", out, "https://egaz-audit.pages.dev") is True
    data = open(out, "rb").read()
    assert len(data) > 10_000
    assert len(re.findall(rb"/Type\s*/Page[^s]", data)) == 1, "1C talabi: karta bir varaq"


def test_precision_metric_uses_inspection_state(conn, tmp_path):
    """8-holat (`yakunlandi_tekshiruv`) kiritilsa — 3-metrika «bor» bo'ladi va to'g'ri sanaydi."""
    from src.murojaat.service import AppealService
    import sqlite3 as _s
    db2 = str(tmp_path / "insp.db")
    c2 = db.connect(db2)
    from src.seed import seed, seed_appeals
    seed(c2)
    codes, _ = seed_appeals(c2)
    svc = AppealService(c2)

    before = [m for m in adolat.accuracy_report(c2)["metrikalar"] if m["nomi"].startswith("Tasdiqlangan")][0]
    assert before["holat"] == "mavjud emas" and before["qiymat"] is None

    # javob_berildi holatidagi murojaatni topib, tekshiruv yakunini yozamiz
    row = c2.execute("SELECT public_code FROM appeals WHERE status='javob_berildi'").fetchone()
    code = row["public_code"] if hasattr(row, "keys") else row[0]
    svc.transition(code, "yakunlandi_tekshiruv", "inspector",
                   evidence="protokol-12.pdf; natija=tasdiqlandi")

    after = [m for m in adolat.accuracy_report(c2)["metrikalar"] if m["nomi"].startswith("Tasdiqlangan")][0]
    assert after["holat"] == "bor" and after["qiymat"] == 1.0
    assert "tasdiqlandi 1" in after["manba"]
    c2.close()


def test_inspection_result_parser():
    assert adolat._insp_result("protokol.pdf; natija=qisman") == "qisman"
    assert adolat._insp_result("natija=Tasdiqlanmadi") == "tasdiqlanmadi"
    assert adolat._insp_result("protokol.pdf") is None
    assert adolat._insp_result(None) is None


# ---------- build_card.py CLI: --out semantikasi (R46) ----------

def _bc():
    import importlib.util, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("build_card", os.path.join(root, "scripts", "build_card.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_out_directory_for_many_targets():
    d, f = _bc().resolve_out_targets("reports/kartalar/", 5)
    assert d == "reports/kartalar/" and f is None


def test_out_file_for_single_target():
    d, f = _bc().resolve_out_targets("/tmp/bitta.html", 1)
    assert d is None and f == "/tmp/bitta.html"


def test_out_file_with_many_targets_rejected():
    with pytest.raises(ValueError, match="katalog"):
        _bc().resolve_out_targets("/tmp/bitta.html", 5)


def test_out_empty_default():
    assert _bc().resolve_out_targets(None, 5) == (None, None)
