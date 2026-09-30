# -*- coding: utf-8 -*-
"""S6 — murojaat moduli testlari (zanjir, SLA, dublikat, anti-spam, append-only)."""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db import connect, init_schema                                    # noqa: E402
from src.murojaat.service import (AppealError, AppealService, add_workdays,  # noqa: E402
                                  haversine_m, trigram_similarity)

MON = datetime(2026, 11, 2, 10, 0, 0)  # dushanba


@pytest.fixture()
def svc(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.execute("INSERT INTO zones VALUES ('Z-YUN','Yunusobod tumani',41.355,69.285,39.0)")
    conn.commit()
    return AppealService(conn)


DESC = "Yunusobod 12-mavzeda kechqurun kuchli tutun hidi sezilmoqda, bir haftadan beri davom etadi."


def _mk(svc, now=MON, **kw):
    body = dict(description=DESC, category="air", lat=41.35, lon=69.28,
                phone="+998900000000", now=now)
    body.update(kw)
    return svc.create(**body)


# ---------- yordamchi funksiyalar ----------
def test_trigram_similarity_identical():
    assert trigram_similarity("abc def ghi", "abc def ghi") == pytest.approx(1.0)


def test_trigram_similarity_different():
    assert trigram_similarity("kechqurun tutun hidi", "kanalizatsiya suvi oqizilmoqda") < 0.3


def test_haversine_300m():
    d = haversine_m(41.3500, 69.2800, 41.3527, 69.2800)  # ~300 m
    assert 280 < d < 320


@pytest.mark.parametrize("days,start,expected", [
    (10, datetime(2026, 11, 2), datetime(2026, 11, 16)),   # 2 dushanba → 16 dushanba
    (10, datetime(2026, 11, 6), datetime(2026, 11, 20)),   # 6 juma → dam olish kunlari o'tkazib
    (5, datetime(2026, 11, 2), datetime(2026, 11, 9)),     # jurnalist
])
def test_add_workdays(days, start, expected):
    assert add_workdays(start, days) == expected


# ---------- validatsiya (§6.4) ----------
def test_short_description_rejected(svc):
    with pytest.raises(AppealError):
        _mk(svc, description="juda qisqa")


def test_bad_category_rejected(svc):
    with pytest.raises(AppealError):
        _mk(svc, category="plastik")


def test_phone_required_unless_anonymous(svc):
    with pytest.raises(AppealError):
        _mk(svc, phone=None)


def test_anonymous_cannot_target_facility(svc):
    with pytest.raises(AppealError):
        _mk(svc, phone=None, author_kind="anonymous", eco_id="E-1001")


def test_anonymous_region_ok(svc):
    a = _mk(svc, phone=None, author_kind="anonymous", zone_id="Z-YUN")
    assert a["status"] == "yuborildi"


# ---------- SLA (§6.5) ----------
def test_sla_deadline_10_workdays(svc):
    a = _mk(svc)
    assert a["sla_deadline"].startswith("2026-11-16")


def test_sla_journalist_5_workdays(svc):
    a = _mk(svc, author_kind="journalist")
    assert a["sla_deadline"].startswith("2026-11-09")


# ---------- holat zanjiri ----------
def test_full_chain_to_resolved(svc):
    a = _mk(svc)
    c = a["public_code"]
    svc.transition(c, "ko'rib_chiqilmoqda", "system", now=MON + timedelta(days=1))
    svc.transition(c, "tashkilotga_yuborildi", "operator", now=MON + timedelta(days=2))
    res = svc.transition(c, "javob_berildi", "operator", now=MON + timedelta(days=3))
    assert res["first_response_at"] is not None
    done = svc.transition(c, "hal_qilindi", "operator", evidence="o'lchov: 18 µg/m³",
                          now=MON + timedelta(days=4))
    assert done["status"] == "hal_qilindi"
    assert len(done["history"]) >= 5


def test_reject_requires_reason(svc):
    a = _mk(svc)
    c = a["public_code"]
    svc.transition(c, "ko'rib_chiqilmoqda", "system", now=MON)
    svc.transition(c, "tashkilotga_yuborildi", "operator", now=MON)
    svc.transition(c, "javob_berildi", "operator", now=MON)
    with pytest.raises(AppealError):
        svc.transition(c, "rad_etildi", "operator", now=MON)


def test_resolve_requires_evidence(svc):
    a = _mk(svc)
    c = a["public_code"]
    svc.transition(c, "ko'rib_chiqilmoqda", "system", now=MON)
    svc.transition(c, "tashkilotga_yuborildi", "operator", now=MON)
    svc.transition(c, "javob_berildi", "operator", now=MON)
    with pytest.raises(AppealError):
        svc.transition(c, "hal_qilindi", "operator", now=MON)


def test_invalid_transition_rejected(svc):
    a = _mk(svc)
    with pytest.raises(AppealError):
        svc.transition(a["public_code"], "hal_qilindi", "operator", evidence="x")


def test_actor_permission_enforced(svc):
    a = _mk(svc)
    c = a["public_code"]
    svc.transition(c, "ko'rib_chiqilmoqda", "system", now=MON)
    with pytest.raises(AppealError):
        svc.transition(c, "tashkilotga_yuborildi", "citizen", now=MON)   # fuqaro qila olmaydi


def test_closed_is_immutable(svc):
    a = _mk(svc)
    c = a["public_code"]
    svc.transition(c, "ko'rib_chiqilmoqda", "system", now=MON)
    svc.transition(c, "tashkilotga_yuborildi", "operator", now=MON)
    svc.transition(c, "hal_qilindi", "operator", evidence="foto", now=MON)
    with pytest.raises(AppealError):
        svc.transition(c, "javob_berildi", "operator", now=MON)


def test_appeal_reopens_review(svc):
    a = _mk(svc)
    c = a["public_code"]
    svc.transition(c, "ko'rib_chiqilmoqda", "system", now=MON)
    svc.transition(c, "tashkilotga_yuborildi", "operator", now=MON)
    svc.transition(c, "javob_berildi", "operator", now=MON)
    svc.transition(c, "rad_etildi", "operator", comment="Manba tasdiqlanmadi", now=MON)
    svc.transition(c, "apellyatsiya", "citizen", now=MON + timedelta(days=1))
    re = svc.transition(c, "ko'rib_chiqilmoqda", "system", now=MON + timedelta(days=2))
    assert re["status"] == "ko'rib_chiqilmoqda"


# ---------- dublikat (§6.4) ----------
def test_duplicate_merge_and_supporters(svc):
    a = _mk(svc)
    b = svc.create(description=DESC, category="air", lat=41.3501, lon=69.2801,
                   phone="+998900000001", now=MON + timedelta(hours=2))
    assert b.get("merged_into") == a["public_code"]
    got = svc.get(a["public_code"])
    assert got["supporters_count"] == 2
    assert any("birlashtirildi" in (e["comment"] or "") for e in got["history"])


def test_weak_similarity_creates_group(svc):
    """0,55–0,85 oralig'i: yangi yozuv alohida qoladi, guruhga qo'shiladi (TZ §6.4)."""
    _mk(svc)
    weak = "Yunusobodda tutun hidi sezilmoqda, kechqurun kuchayadi."
    assert 0.55 <= trigram_similarity(DESC, weak) < 0.85
    b = svc.create(description=weak, category="air",
                   lat=41.3501, lon=69.2801, phone="+998900000002", now=MON + timedelta(hours=1))
    assert b.get("merged_into") is None and b.get("similar_group")


def test_far_away_not_merged(svc):
    _mk(svc)
    b = svc.create(description=DESC, category="air", lat=41.30, lon=69.20,   # ~8 km
                   phone="+998900000003", now=MON + timedelta(hours=1))
    assert b.get("merged_into") is None


# ---------- anti-spam (§6.4) ----------
def test_anti_spam_limit_5_per_day(svc):
    for i in range(5):
        svc.create(description=DESC + f" (nashr {i})", category="air", lat=41.30 + i * 0.01,
                   lon=69.20, phone="+998900000009", now=MON)
    with pytest.raises(AppealError):
        svc.create(description=DESC + " (6-nashr)", category="air", lat=41.31, lon=69.21,
                   phone="+998900000009", now=MON)


# ---------- o'chirish taqiqlangan ----------
def test_delete_refused(svc):
    a = _mk(svc)
    with pytest.raises(PermissionError):
        svc.delete(a["public_code"])


# ---------- SLA hisobot va hodisalar ----------
def test_sla_report_and_events(svc):
    _mk(svc, now=datetime(2026, 11, 1))          # 14 kun oldin (hisobot sanasiga nisbatan)
    rep = svc.sla_report(now=datetime(2026, 11, 15))
    assert rep["open"] == 1 and rep["overdue"] == 1
    ev = svc.due_events(now=datetime(2026, 11, 15))
    assert ev and ev[0]["kind"] in ("overdue", "escalate")


def test_due_events_warn_at_day_7(svc):
    _mk(svc, now=datetime(2026, 11, 8))
    ev = svc.due_events(now=datetime(2026, 11, 15))   # 7 kun
    assert ev and ev[0]["kind"] == "warn"


def test_sla_metrics_compliance(svc):
    a = _mk(svc, now=MON)
    svc.transition(a["public_code"], "ko'rib_chiqilmoqda", "system", now=MON + timedelta(days=1))
    svc.transition(a["public_code"], "tashkilotga_yuborildi", "operator", now=MON + timedelta(days=1))
    svc.transition(a["public_code"], "javob_berildi", "operator", now=MON + timedelta(days=2))
    rep = svc.sla_report(now=MON + timedelta(days=3))
    assert rep["compliance_pct"] == 100.0 and rep["answered"] == 1
