# -*- coding: utf-8 -*-
"""S5 — bot handlerlari testlari (mock rejim: real Telegram kerak emas).

Har bir ssenariy handleri to'g'ridan-to'g'ri chaqiriladi; HTTP klient stub bilan
almashtiriladi. Shunday qilib CI'da ham bot mantiqi sinaladi (token talab qilinmaydi).
"""
import asyncio
import importlib.util
import os
import sys
import types

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)


def load_bot():
    spec = importlib.util.spec_from_file_location("eco_bot", os.path.join(BASE, "scripts", "bot.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bot_mod = load_bot()


# ---------- stublar ----------
class FakeResp:
    def __init__(self, status=200, data=None, text=""):
        self.status_code = status
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class FakeClient:
    """httpx.AsyncClient o'rnini bosuvchi: javoblar navbati bilan qaytariladi."""
    queue: list = []
    calls: list = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, **kw):
        FakeClient.calls.append(("GET", url))
        return FakeClient.queue.pop(0) if FakeClient.queue else FakeResp(200, {})

    async def post(self, url, json=None, **kw):
        FakeClient.calls.append(("POST", url, json))
        return FakeClient.queue.pop(0) if FakeClient.queue else FakeResp(200, {})


class FakeMsg:
    def __init__(self, text="", location=None):
        self.text = text
        self.location = location
        self.sent: list = []

    async def answer(self, text, **kw):
        self.sent.append(text)
        return None


class FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kw):
        self.data.update(kw)

    async def clear(self):
        self.data.clear()

    async def set_state(self, *_):
        pass


@pytest.fixture(autouse=True)
def patch_client(monkeypatch):
    FakeClient.queue.clear()
    FakeClient.calls.clear()
    monkeypatch.setattr(bot_mod.httpx, "AsyncClient", FakeClient)
    yield


def run(coro):
    return asyncio.run(coro)


# ---------- testlar ----------
def test_categories_mapping():
    assert len(bot_mod.CATEGORIES) == 7
    assert len(set(bot_mod.CATEGORIES.values())) == 7
    assert bot_mod.CATEGORIES["Chiqindi"] == "waste"


def test_bot_client_is_optional_without_token():
    # token yo'q muhitda modul import bo'ladi, lekin Bot yaratilmaydi (CI xavfsiz)
    assert os.environ.get("ECO_BOT_TOKEN") or bot_mod.bot is None


def test_start_welcome_text():
    m = FakeMsg("/start")
    run(bot_mod.start(m))
    t = m.sent[0]
    assert "Ochiq-Eko-Ledger" in t and "/murojaat" in t
    assert "«toza» degani emas" in t


def test_holat_usage_without_argument():
    m = FakeMsg("/holat")
    run(bot_mod.holat(m))
    assert "Foydalanish" in m.sent[0]


def test_holat_renders_facility():
    FakeClient.queue.append(FakeResp(200, {
        "facility": {"name": "Sintetik obyekt-7", "eco_id": "E-1007"},
        "class": {"zone_class": "red", "ratio": 2.4, "confidence": 0.7},
        "reasons": ["Normadan 2 baravar va undan ko'p oshgan: R=2.40"],
        "badges": [{"value": 5, "unit": "µg/m³", "ratio": 8.1}]}))
    m = FakeMsg("/holat E-1007")
    run(bot_mod.holat(m))
    t = m.sent[0]
    assert "Sintetik obyekt-7" in t and "red" in t and "R=2.4" in t
    assert "JSST etaloni" in t


def test_tushuntirish_usage_without_argument():
    m = FakeMsg("/tushuntirish")
    run(bot_mod.tushuntirish(m))
    assert "Foydalanish" in m.sent[0]


def test_tushuntirish_renders_three_questions():
    FakeClient.queue.append(FakeResp(200, {
        "eco_id": "E-1007",
        "uch_savol": {"nima_olchandi": "2026-09-25: 217.0 µg/m³ (usul: auto_accredited)",
                      "nega_shunday_qaror": "R = 217.0/35.0 = 6.20 → Qizil (R ≥ 2,0)",
                      "qanday_etiroz": "Botdan /murojaat; javob 10 kunda; apellyatsiya — 30 ish kuni"},
        "kartochka": {"4_noaniqlik_U": {"holat": "mavjud emas"},
                      "9_koeffitsient": {"holat": "qo'llanilmaydi"}}}))
    m = FakeMsg("/tushuntirish E-1007")
    run(bot_mod.tushuntirish(m))
    t = m.sent[0]
    assert "Tushuntirish kartasi" in t and "6.20" in t and "30 ish kuni" in t
    assert "to'lmagan maydon: 1 ta" in t          # faqat «mavjud emas» sanaladi, «qo'llanilmaydi» emas


def test_tushuntirish_404_message():
    FakeClient.queue.append(FakeResp(404, {"detail": "Obyekt topilmadi"}))
    m = FakeMsg("/tushuntirish E-9999")
    run(bot_mod.tushuntirish(m))
    assert "topilmadi" in m.sent[0]


def test_holat_404_message():
    FakeClient.queue.append(FakeResp(404, {"detail": "Obyekt topilmadi"}))
    m = FakeMsg("/holat E-9999")
    run(bot_mod.holat(m))
    assert "topilmadi" in m.sent[0]


def test_xarita_lists_zones_and_blue_rule():
    FakeClient.queue.append(FakeResp(200, {"features": [
        {"properties": {"name": "Yunusobod", "zone_color": "red", "coverage": 1.0, "measured": 21, "facilities": 21}},
        {"properties": {"name": "Olmazor", "zone_color": "blue", "coverage": 0.46, "measured": 5, "facilities": 11}}]}))
    m = FakeMsg("/xarita")
    run(bot_mod.xarita(m))
    t = m.sent[0]
    assert "Yunusobod" in t and "🔴" in t and "Olmazor" in t and "46%" in t
    assert "toza emas" in t


def test_sla_panel():
    FakeClient.queue.append(FakeResp(200, {"total": 8, "open": 5, "median_response_days": 4.0,
                                           "compliance_pct": 100.0, "overdue_pct": 20.0}))
    m = FakeMsg("/sla")
    run(bot_mod.sla(m))
    t = m.sent[0]
    assert "Median javob: 4.0" in t and "100.0%" in t


def test_kuzatish_requires_code():
    m = FakeMsg("/kuzatish")
    run(bot_mod.kuzatish(m))
    assert "Foydalanish" in m.sent[0]


def test_kuzatish_shows_chain_and_no_delete_note():
    FakeClient.queue.append(FakeResp(200, {"public_code": "A-2026-000001", "status": "ko'rib_chiqilmoqda",
                                           "sla_deadline": "2026-10-12T10:00:00",
                                           "history": [{"to_status": "yuborildi"}, {"to_status": "ko'rib_chiqilmoqda"}]}))
    m = FakeMsg("/kuzatish A-2026-000001")
    run(bot_mod.kuzatish(m))
    t = m.sent[0]
    assert "yuborildi → ko'rib_chiqilmoqda" in t and "o'chirilmaydi" in t


def test_murojaat_description_too_short():
    m = FakeMsg("juda qisqa")
    run(bot_mod.murojaat_loc(m, FakeState()))
    assert "kamida 30 belgi" in m.sent[0]


def test_murojaat_location_step_advances():
    st = FakeState()
    loc = types.SimpleNamespace(latitude=41.31, longitude=69.24)
    m = FakeMsg("📍 Lokatsiyani yuborish", location=loc)
    run(bot_mod.murojaat_loc(FakeMsg("a" * 35), st)) if False else None
    run(bot_mod.murojaat_loc(FakeMsg("a" * 35), st)) if False else None
    # to'g'ridan-to'g'ri lokatsiya qadami:
    run(bot_mod.murojaat_phone(m, st))
    assert st.data["lat"] == 41.31 and st.data["lon"] == 69.24
    assert "Telefon" in m.sent[0]


def test_murojaat_send_merged_response():
    FakeClient.queue.append(FakeResp(200, {"merged_into": "A-2026-000003", "similarity": 0.91,
                                           "supporters_count": 4, "public_code": "A-2026-000003"}))
    st = FakeState({"category": "odor", "description": "x" * 40, "lat": 41.3, "lon": 69.3})
    m = FakeMsg("+998901234567")
    run(bot_mod.murojaat_send(m, st))
    t = m.sent[0]
    assert "birlashtirildi" in t and "A-2026-000003" in t and "yo'qolmadi" in t
    assert st.data == {}          # FSM tozalandi


def test_murojaat_send_new_appeal():
    FakeClient.queue.append(FakeResp(200, {"public_code": "A-2026-000009", "sla_deadline": "2026-10-14T10:00:00"}))
    st = FakeState({"category": "air", "description": "y" * 45, "lat": 41.2, "lon": 69.2})
    m = FakeMsg("+998971112233")
    run(bot_mod.murojaat_send(m, st))
    t = m.sent[0]
    assert "A-2026-000009" in t and "2026-10-14" in t and "/kuzatish" in t
    # API'ga to'g'ri payload ketdi
    method, url, payload = FakeClient.calls[-1]
    assert method == "POST" and url.endswith("/v1/appeals")
    assert payload["category"] == "air" and payload["lat"] == 41.2 and payload["phone"] == "+998971112233"
    assert payload["appeal_type"] == "T1" and payload["publication_consent"] == "partial"


def test_murojaat_send_handles_api_error():
    FakeClient.queue.append(FakeResp(400, text="Kategoriya noto'g'ri"))
    st = FakeState({"category": "air", "description": "z" * 40, "lat": 41.0, "lon": 69.0})
    m = FakeMsg("+998900000000")
    run(bot_mod.murojaat_send(m, st))
    assert "Yuborilmadi" in m.sent[0]


def test_location_keyboard_has_location_button():
    kb = bot_mod.kb_location.keyboard
    assert kb[0][0].request_location is True
