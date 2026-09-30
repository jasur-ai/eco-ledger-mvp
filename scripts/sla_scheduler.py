#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SLA push-eslatmalar job'i (TZ §6.5: 7/10/15-kun).

Ishlash tartibi:
    python3 scripts/sla_scheduler.py --once                 # bir sikl (cron uchun)
    python3 scripts/sla_scheduler.py --interval 1800        # doimiy (30 daqiqa)

Kerakli muhit o'zgaruvchilari:
    ECO_BOT_TOKEN yoki TELEGRAM_BOT_TOKEN_ECO   — bot tokeni
    ECO_ADMIN_CHAT_ID (yoki TELEGRAM_ADMIN_ID)  — eskalatsiya xabarlari uchun operator chat
    ECO_API (ixtiyoriy, faqat log uchun)        — http://127.0.0.1:8000

Matn qoidasi: raqam registrdan, jumlalar shablon (src/notify/scheduler.py).
Bitta hodisa (warn/overdue/escalate) har bir chat uchun BIR MARTA yuboriladi.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from src import db                                    # noqa: E402
from src.murojaat.service import AppealService        # noqa: E402
from src import notify                                # noqa: E402


def env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v.strip()
    return default


def telegram_sender(token: str):
    """Telegram Bot API orqali yuboruvchi (urllib — qo'shimcha bog'liqlik yo'q)."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send(chat_id: int, text: str) -> bool:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        try:
            with urllib.request.urlopen(url, data=data, timeout=20) as r:
                body = json.loads(r.read().decode())
                return bool(body.get("ok"))
        except Exception as e:            # noqa: BLE001
            print(f"  ✗ chat {chat_id}: {type(e).__name__}: {str(e)[:120]}")
            return False

    return send


def admin_chats() -> tuple[int, ...]:
    raw = env("ECO_ADMIN_CHAT_IDS", "ECO_ADMIN_CHAT_ID", "TELEGRAM_ADMIN_ID")
    out = []
    for part in raw.replace(" ", "").split(","):
        if part.lstrip("-").isdigit():
            out.append(int(part))
    return tuple(out)


def cycle(sender, dry_run: bool = False) -> dict:
    conn = db.connect()
    svc = AppealService(conn)
    res = notify.run_once(conn, sender if not dry_run else (lambda c, t: True), svc,
                          admin_chats=admin_chats())
    conn.close()
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="SLA push-eslatmalar job'i")
    ap.add_argument("--once", action="store_true", help="bitta sikl (cron uchun)")
    ap.add_argument("--interval", type=int, default=0, help="doimiy rejim: sekundlarda oraliq")
    ap.add_argument("--dry-run", action="store_true", help="yubormasdan sinash (hech narsa jo'natilmaydi)")
    args = ap.parse_args()

    token = env("ECO_BOT_TOKEN", "TELEGRAM_BOT_TOKEN_ECO")
    if not token and not args.dry_run:
        print("❌ Token topilmadi: ECO_BOT_TOKEN yoki TELEGRAM_BOT_TOKEN_ECO o'rnating "
              "(yoki --dry-run bilan sinang).", file=sys.stderr)
        return 2

    sender = telegram_sender(token) if token else (lambda c, t: True)
    print(f"⏱  SLA scheduler · admin chatlar: {admin_chats() or '—'} · "
          f"rejim: {'dry-run' if args.dry_run else ('bir sikl' if args.once or not args.interval else f'doimiy {args.interval}s')}")

    while True:
        t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            res = cycle(sender, dry_run=args.dry_run)
            print(f"[{t0}] hodisalar: {res['events']} {res['kinds']} · navbat: {res['queued']} · "
                  f"yuborildi: {res['sent']} · xato: {res['failed']}")
        except Exception as e:            # noqa: BLE001 — job to'xtamasligi kerak
            print(f"[{t0}] ❌ sikl xatosi: {type(e).__name__}: {e}")
        if args.once or not args.interval:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
