# -*- coding: utf-8 -*-
"""S6 qo'shimcha — push-eslatmalar (TZ §6.5: 7/10/15-kun).

Vazifa: murojaat muddatlari haqida fuqaroga (bot orqali) va operatorga avtomatik xabar.
Tamoyillar:
  • Bitta hodisa turi bir marta yuboriladi (warn/overdue/escalate) — spam yo'q, `notification_log` bilan.
  • Faqat ro'yxatdan o'tgan chat'larga (fuqaro murojaatni bot orqali yuborganda obuna bo'ladi).
  • Eskalatsiya (muddatdan 5 kun oshgan) — operator chat'lariga ham boradi.
  • Matn — LLM emas, shablon: raqam registrdan, tayyor jumlalar (6 qavat verifikatsiya talab qilinmaydi,
    chunki o'zgaruvchan qiymat yo'q — bu ongli yechim).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime

BASEDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(BASEDIR, "src")

KINDS = ("warn", "overdue", "escalate")

SAFETY = """Hayotiy xavfsizlik:
- Faqat raqamlar registrdan: `code`, `age_days`, `appeal_id`, `status`, `public_code`.
- Xavfli so'zlar (`tavsiya`, `yopish`, `jarima`, `ayblovchi`) QO'LLANILMAYDI.
- Matn audit qilinadi: `notification_log` bilan birga saqlanadi.
"""


def safety_note() -> str:
    return SAFETY


def build_message(event: dict, appeal: dict) -> str:
    """Hodisa turi bo'yicha fuqaro uchun xabar (o'zgaruvchan faqat registr qiymatlari)."""
    code, age = event["code"], event.get("age_days")
    status = appeal.get("status", "—")
    if event["kind"] == "warn":
        return (f"⏳ {code} murojaatingiz 7 kundan oshdi.\n"
                f"Holat: {status}\n"
                f"Javob muddati: {appeal['sla_deadline'][:10]}\n"
                f"Kuzatish: /kuzatish {code}")
    if event["kind"] == "overdue":
        return (f"⚠️ {code} murojaatingiz muddati o'tgan.\n"
                f"Muddati: {appeal['sla_deadline'][:10]} · kechikish: {age} kun\n"
                f"Holat: {status}\n"
                f"Sizning davolanish tashkiloti KPI panelida ko'rinadi.")
    if event["kind"] == "escalate":
        return (f"🔴 {code} murojaatingiz bo'yicha javob {age} kunga cho'zildi.\n"
                f"Muddat (10 ish kuni) oshib ketdi, kechikish: {age} kun.\n"
                f"Holat: {status}\n"
                f"Kechikish sababini ko'rish: /kuzatish {code}")
    raise ValueError(f"Noma'lum hodisa turi: {event['kind']}")


def build_admin_message(event: dict, appeal: dict) -> str:
    return (f"🚨 ESKALATSIYA · {event['code']}\n"
            f"Kechikish: {event.get('age_days')} kun · holat: {appeal.get('status')}\n"
            f"Javob muddati: {appeal['sla_deadline'][:10]}\n"
            f"KPI paneli: /sla")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Mavjud bazalarni ham qo'llab-quvvatlash uchun (idempotent)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bot_subscriptions (
          chat_id     INTEGER NOT NULL,
          public_code TEXT NOT NULL,
          created_at  TEXT NOT NULL DEFAULT (datetime('now')),
          PRIMARY KEY (chat_id, public_code)
        );
        CREATE TABLE IF NOT EXISTS notification_log (
          event_key  TEXT PRIMARY KEY,
          code       TEXT,
          kind       TEXT,
          chat_id    INTEGER,
          sent_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


def subscribe(conn: sqlite3.Connection, chat_id: int, public_code: str) -> dict:
    ensure_schema(conn)
    row = conn.execute("SELECT 1 FROM appeals WHERE public_code=?", (public_code,)).fetchone()
    if not row:
        raise ValueError(f"Murojaat topilmadi: {public_code}")
    conn.execute("INSERT OR IGNORE INTO bot_subscriptions(chat_id, public_code) VALUES (?,?)",
                 (int(chat_id), public_code))
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM bot_subscriptions WHERE public_code=?", (public_code,)).fetchone()[0]
    return {"chat_id": int(chat_id), "public_code": public_code, "subscribers": n}


def subscriptions_of(conn: sqlite3.Connection, chat_id: int) -> list[str]:
    ensure_schema(conn)
    return [r["public_code"] for r in conn.execute(
        "SELECT public_code FROM bot_subscriptions WHERE chat_id=? ORDER BY created_at", (int(chat_id),))]


def _already_sent(conn, event_key: str) -> bool:
    return conn.execute("SELECT 1 FROM notification_log WHERE event_key=?", (event_key,)).fetchone() is not None


def _log(conn, event_key, code, kind, chat_id) -> None:
    conn.execute("INSERT OR IGNORE INTO notification_log(event_key, code, kind, chat_id) VALUES (?,?,?,?)",
                 (event_key, code, kind, chat_id))


def due_notifications(conn: sqlite3.Connection, due_events: list[dict], appeals: dict[str, dict],
                      admin_chats: tuple[int, ...] = ()) -> list[dict]:
    """Yuborilishi kerak bo'lgan xabarlar ro'yxati (dedupe bilan).

    `appeals` — {public_code: appeal dict} (AppealService.get natijasi).
    Qaytadi: [{event_key, chat_id, text, kind, code, admin}]
    """
    ensure_schema(conn)
    out = []
    for ev in due_events:
        code = ev["code"]
        appeal = appeals.get(code)
        if appeal is None:
            continue
        ev_key = f"{code}:{ev['kind']}"
        text = build_message(ev, appeal)
        notified_chats: set[int] = set()
        for r in conn.execute("SELECT chat_id FROM bot_subscriptions WHERE public_code=?", (code,)):
            item_key = f"{ev_key}#{r['chat_id']}"
            if _already_sent(conn, item_key):
                continue
            notified_chats.add(int(r["chat_id"]))
            out.append({"event_key": item_key, "chat_id": r["chat_id"],
                        "text": text, "kind": ev["kind"], "code": code, "admin": False})
        if ev["kind"] == "escalate":
            admin_text = build_admin_message(ev, appeal)
            for chat in admin_chats:
                if int(chat) in notified_chats:      # o'sha chat fuqaro matnini oldi — takror yubormaymiz
                    continue
                item_key = f"{ev_key}#admin{chat}"
                if _already_sent(conn, item_key):
                    continue
                out.append({"event_key": item_key, "chat_id": chat,
                            "text": admin_text, "kind": ev["kind"],
                            "code": code, "admin": True})
    return out


def run_once(conn: sqlite3.Connection, sender, service, now: datetime | None = None,
             admin_chats: tuple[int, ...] = ()) -> dict:
    """Bir sikl: hodisalarni yig'ib, xabarlarni yuboradi va jurnalga yozadi.

    `sender(chat_id, text) -> bool` — haqiqiy Telegram yoki test-stub.
    """
    due = service.due_events(now)
    appeals = {ev["code"]: service.get(ev["code"]) for ev in due}
    todo = due_notifications(conn, due, appeals, admin_chats)
    sent, failed = 0, 0
    for item in todo:
        ok = False
        try:
            ok = bool(sender(item["chat_id"], item["text"]))
        except Exception:                                     # tarmoq xatosi — jurnalga yozilmaydi
            ok = False
        if ok:
            _log(conn, item["event_key"], item["code"], item["kind"], item["chat_id"])
            sent += 1
        else:
            failed += 1
    conn.commit()
    return {"events": len(due), "queued": len(todo), "sent": sent, "failed": failed,
            "kinds": {k: sum(1 for e in due if e["kind"] == k) for k in KINDS}}
