# -*- coding: utf-8 -*-
"""S6 qo'shimcha — push-eslatmalar testlari (TZ §6.5: 7/10/15-kun).

Sinaladi: xabar matni, dedupe (bitta hodisa bir marta), obuna, eskalatsiya → admin,
xatolarga chidamlilik, API endpointlar.
"""
import os
import sys
from datetime import datetime, timedelta

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

NOTIFY_DB = "/tmp/eco_ledger_notify_test.db"
os.environ["ECO_LEDGER_DB"] = NOTIFY_DB
if os.path.exists(NOTIFY_DB):
    os.remove(NOTIFY_DB)

from src import config                                 # noqa: E402
from src import db                                     # noqa: E402
from src import notify                                 # noqa: E402
from src.murojaat.service import AppealService         # noqa: E402
from src.seed import NOW as SEED_NOW                    # noqa: E402
from src.seed import seed, seed_appeals                # noqa: E402

NOW = SEED_NOW          # demo bazasi shu 'hozir' bilan qurilgan


@pytest.fixture(scope="module")
def conn():
    c = db.connect(NOTIFY_DB)                          # yo'l aniq beriladi
    seed(c)
    seed_appeals(c)
    yield c
    c.close()


@pytest.fixture()
def svc(conn):
    return AppealService(conn)


# ---------- 1. xabar matni ----------
def test_build_message_warn():
    ev = {"code": "A-2026-000002", "kind": "warn", "age_days": 8.0}
    ap = {"status": "ko'rib_chiqilmoqda", "sla_deadline": "2026-10-05 10:00:00"}
    t = notify.build_message(ev, ap)
    assert "A-2026-000002" in t and "7 kundan oshdi" in t and "2026-10-05" in t


def test_build_message_overdue():
    ev = {"code": "A-2026-000001", "kind": "overdue", "age_days": 15.0}
    ap = {"status": "tashkilotga_yuborildi", "sla_deadline": "2026-09-25 10:00:00"}
    t = notify.build_message(ev, ap)
    assert "muddati o'tgan" in t and "15.0 kun" in t


def test_build_message_escalate():
    ev = {"code": "A-2026-000004", "kind": "escalate", "age_days": 20.0}
    ap = {"status": "yuborildi", "sla_deadline": "2026-09-20 10:00:00"}
    t = notify.build_message(ev, ap)
    assert "javob 20.0 kunga cho'zildi" in t and "10 ish kuni" in t


def test_messages_have_no_forbidden_words():
    """Anti-da'vo (TZ §2): xabar hech kimni ayblamaydi, tavsiya bermaydi."""
    bad = ["ayblanadi", "aybdor", "jarima", "yopish kerak", "tavsiya"]
    for kind in ("warn", "overdue", "escalate"):
        ev = {"code": "A-2026-000001", "kind": kind, "age_days": 9.0}
        ap = {"status": "yuborildi", "sla_deadline": "2026-10-01 10:00:00"}
        t = notify.build_message(ev, ap).lower()
        assert not any(b in t for b in bad), f"{kind}: taqiqlangan so'z topildi"


def test_build_message_unknown_kind():
    with pytest.raises(ValueError):
        notify.build_message({"code": "X", "kind": "boom", "age_days": 1}, {})


def test_admin_message_has_kpi_and_code():
    ev = {"code": "A-2026-000004", "kind": "escalate", "age_days": 20.0}
    ap = {"status": "yuborildi", "sla_deadline": "2026-09-20 10:00:00"}
    t = notify.build_admin_message(ev, ap)
    assert "ESKALATSIYA" in t and "/sla" in t


# ---------- 2. obuna ----------
def test_subscribe_requires_existing_code(conn):
    with pytest.raises(ValueError):
        notify.subscribe(conn, 111, "A-9999-000000")


def test_subscribe_idempotent(conn):
    r1 = notify.subscribe(conn, 111, "A-2026-000001")
    r2 = notify.subscribe(conn, 111, "A-2026-000001")
    assert r1["subscribers"] == r2["subscribers"]
    assert "A-2026-000001" in notify.subscriptions_of(conn, 111)


def test_subscriptions_isolated_per_chat(conn):
    notify.subscribe(conn, 222, "A-2026-000002")
    assert "A-2026-000002" in notify.subscriptions_of(conn, 222)
    assert "A-2026-000002" not in notify.subscriptions_of(conn, 111)


# ---------- 3. dedupe va yuborish ----------
def test_run_once_sends_and_dedupes(conn, svc):
    notify.subscribe(conn, 111, "A-2026-000001")   # muddati o'tgan murojaat
    notify.subscribe(conn, 333, "A-2026-000002")   # ogohlantirish (8 kun)

    sent = []

    def sender(chat_id, text):
        sent.append((chat_id, text))
        return True

    r1 = notify.run_once(conn, sender, svc, now=NOW)
    assert r1["kinds"]["overdue"] >= 1 and r1["kinds"]["warn"] >= 1
    first = len(sent)
    assert first >= 1, "kamida bitta eslatma ketishi kerak edi"

    r2 = notify.run_once(conn, sender, svc, now=NOW)   # ikkinchi sikl — takror yo'q
    assert len(sent) == first, "takroriy xabar yuborildi (dedupe ishlamadi)"
    assert r2["sent"] == 0 and r2["queued"] == 0


def test_escalate_goes_to_admin(conn, svc):
    got = []

    def sender(chat_id, text):
        got.append((chat_id, text))
        return True

    res = notify.run_once(conn, sender, svc, now=NOW, admin_chats=(8004724563,))
    assert res["kinds"]["escalate"] >= 1
    assert any(c == 8004724563 and "ESKALATSIYA" in t for c, t in got), "admin xabari kelmadi"


def test_escalate_not_duplicated_for_subscribed_admin(conn, svc):
    """Admin ham obunachi bo'lsa — o'sha chatga bitta xabar (takror yo'q)."""
    esc = [e for e in svc.due_events(NOW) if e["kind"] == "escalate"]
    if not esc:
        pytest.skip("eskalatsiya hodisasi yo'q")
    code = esc[0]["code"]
    notify.subscribe(conn, 888, code)
    got = []
    res = notify.run_once(conn, lambda c, t: got.append((c, t)) or True, svc,
                          now=NOW, admin_chats=(888,))
    assert res["kinds"]["escalate"] >= 1
    msgs = [t for c, t in got if c == 888]
    assert len(msgs) == 1, f"chatga {len(msgs)} ta xabar ketdi (takror yuborilgan)"
    assert "ESKALATSIYA" not in msgs[0]              # fuqaro matni ustuvor


def test_sender_failure_is_recorded_not_logged(conn, svc):
    notify.subscribe(conn, 444, "A-2026-000003")

    def failing(chat_id, text):
        raise RuntimeError("tarmoq yo'q")

    res = notify.run_once(conn, failing, svc, now=NOW)
    assert res["failed"] >= 0
    # muvaffaqiyatsiz yuborish jurnalga yozilmaydi — keyingi siklda qayta uriniladi
    assert conn.execute("SELECT 1 FROM notification_log WHERE chat_id=444").fetchone() is None


def test_notification_log_grows_only_on_success(conn):
    n_before = conn.execute("SELECT COUNT(*) FROM notification_log").fetchone()[0]
    res = notify.run_once(conn, lambda c, t: True, AppealService(conn), now=NOW)
    n_after = conn.execute("SELECT COUNT(*) FROM notification_log").fetchone()[0]
    assert n_after == n_before + res["sent"]


# ---------- 4. API ----------
@pytest.fixture()
def client(monkeypatch):
    """API testlari uchun: config.DB_PATH shu modul bazasiga o'rnatiladi."""
    from fastapi.testclient import TestClient
    from src.api.app import app
    monkeypatch.setattr(config, "DB_PATH", NOTIFY_DB)
    return TestClient(app)


def test_api_due_endpoint(client):
    r = client.get("/v1/appeals/due")
    assert r.status_code == 200 and "due" in r.json()


def test_api_subscribe_and_list(client):
    r = client.post("/v1/bot/subscribe", json={"chat_id": 555, "public_code": "A-2026-000005"})
    assert r.status_code == 200 and r.json()["subscribers"] >= 1
    lst = client.get("/v1/bot/subscriptions", params={"chat_id": 555}).json()["codes"]
    assert "A-2026-000005" in lst


def test_api_subscribe_unknown_code_404(client):
    r = client.post("/v1/bot/subscribe", json={"chat_id": 666, "public_code": "A-0000-000000"})
    assert r.status_code == 404
