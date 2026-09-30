# -*- coding: utf-8 -*-
"""S5 — Telegram bot (aiogram 3) — @eco_ledger_bot uchun to'liq klient.

Ishga tushirish:
    export ECO_BOT_TOKEN="123456:ABC..."
    export ECO_API="http://127.0.0.1:8000"
    python3 scripts/bot.py

Bot faqat API bilan ishlaydi (DB'ga tegmaydi) — yupqa klient.
6 ssenariy: /start · /holat · /xarita · /murojaat (FSM) · /kuzatish · /sla
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (KeyboardButton, Message, ReplyKeyboardMarkup,
                           ReplyKeyboardRemove)

API = os.environ.get("ECO_API", "http://127.0.0.1:8000")
TOKEN = os.environ.get("ECO_BOT_TOKEN")

bot = Bot(TOKEN) if TOKEN else None
dp = Dispatcher()

CATEGORIES = {"Havo": "air", "Suv": "water", "Chiqindi": "waste",
              "Shovqin": "noise", "Hid": "odor", "Tuproq": "soil", "Boshqa": "other"}

kb_categories = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=c) for c in list(CATEGORIES)[:3]],
              [KeyboardButton(text=c) for c in list(CATEGORIES)[3:6]],
              [KeyboardButton(text="Boshqa")]],
    resize_keyboard=True, one_time_keyboard=True)

kb_location = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
              [KeyboardButton(text="Bekor qilish")]],
    resize_keyboard=True, one_time_keyboard=True)


class Appeal(StatesGroup):
    category = State()
    description = State()
    location = State()
    phone = State()


# ---------------- ssenariy 1: /start ----------------
@dp.message(Command("start"))
async def start(m: Message):
    await m.answer(
        "🌿 <b>Ochiq-Eko-Ledger</b> botiga xush kelibsiz!\n\n"
        "Buyruqlar:\n"
        "/holat &lt;eco_id&gt; — obyektning rangi va sabablari (masalan: E-1001)\n"
        "/xarita — zonalar ro'yxati va qamrov\n"
        "/murojaat — shikoyat yuborish (12 maydon)\n"
        "/kuzatish &lt;kod&gt; — murojaat holati va muddati\n"
        "/sla — ochiq xizmat ko'rsatish paneli\n\n"
        "ℹ️ Ko'k-neytral zona «ma'lumot yo'q/tekshirilmagan» degani — «toza» degani emas.",
        parse_mode="HTML")


# ---------------- ssenariy 2: /holat ----------------
@dp.message(Command("holat"))
async def holat(m: Message):
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Foydalanish: /holat E-1001")
        return
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{API}/v1/facilities/{parts[1].strip()}")
    if r.status_code != 200:
        await m.answer("Obyekt topilmadi (eco_id ni tekshiring).")
        return
    d = r.json()
    cls = d["class"] or {}
    reasons = "\n".join(f"• {x}" for x in d["reasons"][:3])
    badge = ""
    if d["badges"]:
        b = d["badges"][0]
        badge = f"\n🌍 JSST etaloni: {b['value']} {b['unit']} → nisbat {b['ratio']}×"
    await m.answer(
        f"<b>{d['facility']['name']}</b> ({d['facility']['eco_id']})\n"
        f"Rang: <b>{cls.get('zone_class','—')}</b> · R={cls.get('ratio')} · C={cls.get('confidence')}\n"
        f"{reasons}{badge}", parse_mode="HTML")


# ---------------- ssenariy 3: /xarita ----------------
@dp.message(Command("xarita"))
async def xarita(m: Message):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{API}/v1/geo/zones.geojson")
    feats = r.json().get("features", [])
    emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢", "blue": "🔵"}
    lines = [f"{emoji.get(f['properties']['zone_color'],'⚪')} <b>{f['properties']['name']}</b> — "
             f"qamrov {round(100*f['properties']['coverage'])}% "
             f"({f['properties']['measured']}/{f['properties']['facilities']})" for f in feats]
    await m.answer("🗺 <b>Zonalar</b> (rule 1.0):\n" + "\n".join(lines) +
                   "\n\n🔵 = ma'lumot yetarli emas (toza emas!)", parse_mode="HTML")


# ---------------- ssenariy 4: /murojaat (FSM) ----------------
@dp.message(Command("murojaat"))
async def murojaat_start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("1/4 — Qaysi turdagi muammo?", reply_markup=kb_categories)
    await state.set_state(Appeal.category)


@dp.message(Appeal.category, F.text.in_(list(CATEGORIES)))
async def murojaat_desc(m: Message, state: FSMContext):
    await state.update_data(category=CATEGORIES[m.text])
    await m.answer("2/4 — Muammoni tasvirlab yozing (30–2000 belgi).", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Appeal.description)


@dp.message(Appeal.description, F.text)
async def murojaat_loc(m: Message, state: FSMContext):
    if len(m.text.strip()) < 30:
        await m.answer("Juda qisqa — kamida 30 belgi yozing.")
        return
    await state.update_data(description=m.text.strip())
    await m.answer("3/4 — Voqea joyini yuboring.", reply_markup=kb_location)
    await state.set_state(Appeal.location)


@dp.message(Appeal.location, F.location)
async def murojaat_phone(m: Message, state: FSMContext):
    await state.update_data(lat=m.location.latitude, lon=m.location.longitude)
    await m.answer("4/4 — Telefon raqamingizni yozing (tasdiqlash uchun; +998...).",
                   reply_markup=ReplyKeyboardRemove())
    await state.set_state(Appeal.phone)


@dp.message(Appeal.phone, F.text, ~F.text.startswith("Bekor"))
async def murojaat_send(m: Message, state: FSMContext):
    data = await state.get_data()
    payload = {"appeal_type": "T1", "category": data["category"], "description": data["description"],
               "lat": data["lat"], "lon": data["lon"], "phone": m.text.strip(),
               "author_kind": "individual", "publication_consent": "partial"}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{API}/v1/appeals", json=payload)
    await state.clear()
    if r.status_code != 200:
        await m.answer(f"❌ Yuborilmadi: {r.text[:200]}")
        return
    d = r.json()
    if d.get("merged_into"):
        await m.answer(f"✅ Murojaatingiz mavjud <b>{d['merged_into']}</b> bilan birlashtirildi "
                       f"(o'xshashlik {d['similarity']}, qo'llab-quvvatlovchilar {d['supporters_count']}). "
                       f"U yo'qolmadi — kuchini oshirdi.", parse_mode="HTML")
    else:
        await m.answer(f"✅ Qabul qilindi: <b>{d['public_code']}</b>\n"
                       f"Javob muddati: {d['sla_deadline'][:10]} (10 ish kuni)\n"
                       f"Holatni kuzatish: /kuzatish {d['public_code']}\n"
                       f"ℹ️ Muddat nazorati yoqildi — 7/10/15-kunlarda avtomatik eslatma keladi.",
                       parse_mode="HTML")
        await _subscribe(m, d["public_code"])


# ---------------- ssenariy 5: /kuzatish ----------------
async def _subscribe(m: Message, code: str) -> None:
    """Chat'ni murojaatga obuna qiladi (eslatmalar uchun) — xato holatda jim o'tadi."""
    chat_id = getattr(getattr(m, "chat", None), "id", None)
    if not chat_id:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            await c.post(f"{API}/v1/bot/subscribe", json={"chat_id": chat_id, "public_code": code})
    except Exception:
        pass


@dp.message(Command("eslatmalar"))
async def eslatmalar(m: Message):
    """Obuna bo'lgan murojaatlar ro'yxati."""
    chat_id = getattr(getattr(m, "chat", None), "id", None)
    if not chat_id:
        await m.answer("Chat aniqlanmadi.")
        return
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{API}/v1/bot/subscriptions", params={"chat_id": chat_id})
    codes = r.json().get("codes", [])
    if not codes:
        await m.answer("📭 Hozircha eslatma yo'q. Murojaat yuboring (/murojaat) — muddat nazorati avtomatik yoqiladi.")
        return
    await m.answer("🔔 <b>Kuzatilayotgan murojaatlar</b> (7/10/15-kun eslatmalari yoqilgan):\n"
                   + "\n".join(f"• /kuzatish {c}" for c in codes), parse_mode="HTML")


@dp.message(Command("kuzatish"))
async def kuzatish(m: Message):
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Foydalanish: /kuzatish A-2026-000001")
        return
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{API}/v1/appeals/{parts[1].strip()}")
    if r.status_code != 200:
        await m.answer("Murojaat topilmadi.")
        return
    d = r.json()
    await _subscribe(m, d["public_code"])
    chain = " → ".join(f"{h['to_status']}" for h in d["history"])
    await m.answer(f"<b>{d['public_code']}</b> — <b>{d['status']}</b>\n"
                   f"Muddat: {d['sla_deadline'][:16]}\n"
                   f"Zanjir: {chain}\n"
                   f"ℹ️ Yozuvlar o'chirilmaydi — har o'zgarish tarixda qoladi.", parse_mode="HTML")


# ---------------- ssenariy 6: /sla ----------------
@dp.message(Command("sla"))
async def sla(m: Message):
    async with httpx.AsyncClient(timeout=20) as c:
        d = (await c.get(f"{API}/v1/kpi/sla")).json()
    await m.answer(
        f"📊 <b>Ochiq xizmat paneli</b>\n"
        f"Jami murojaat: {d['total']} · ochiq: {d['open']}\n"
        f"Median javob: {d['median_response_days']} kun\n"
        f"Muddatga rioya: {d['compliance_pct']}%\n"
        f"Muddati o'tgan ulush: {d['overdue_pct']}%", parse_mode="HTML")


@dp.message(Command("bekor"))
async def bekor(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())


async def main():
    if bot is None:
        raise SystemExit("ECO_BOT_TOKEN o'rnatilmagan. export ECO_BOT_TOKEN=... qilib qayta ishga tushiring.")
    me = await bot.get_me()
    print(f"Bot ishga tushdi: @{me.username} · API: {API}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
