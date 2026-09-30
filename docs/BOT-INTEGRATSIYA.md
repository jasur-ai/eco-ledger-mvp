# Telegram bot integratsiyasi (S5) — qanday ulash

> **Yangilangan (2026-09-30): bot tayyor va JONLI ishlayapti** — to'liq kod `scripts/bot.py`
> (aiogram 3), token bilan ishga tushirilgan: **[@ecoledg_bot](https://t.me/ecoledg_bot)**.
> Operator qo'llanmasi: `docs/BOT-ISHLATISH.md`. Bot — **yupqa klient**: faqat API'ga murojaat qiladi,
> DB'ga to'g'ridan-to'g'ri tegmaydi.

## 1. Ssenariylar ↔ API endpointlar (kod ↔ shartnoma)

| Bot buyrug'i | API | Kod (bot.py) izohi |
|---|---|---|
| `/start` | — | salomlashuv, «ko'k ≠ toza» qoidasi |
| `/holat <eco_id>` | `GET /v1/facilities/{eco_id}` | rang, R, C, sabablar (3), JSST yorlig'i |
| `/xarita` | `GET /v1/geo/zones.geojson` | 6 zona: rang emoji, qamrov %, o'lchov/obyekt |
| `/murojaat` (FSM: 4 qadam) | `POST /v1/appeals` | kategoriya → tavsif(30+) → lokatsiya → telefon |
| `/kuzatish <kod>` | `GET /v1/appeals/{code}` | holat zanjiri + SLA muddati |
| `/sla` | `GET /v1/kpi/sla` | ochiq KPI panel |
| `/bekor` | — | FSM jarayonini to'xtatish |

Dublikat bo'lganda API `merged_into` qaytaradi va bot buni foydalanuvchiga tushunarli tilda aytadi
(«birlashtirildi … yo'qolmadi, kuchini oshirdi»).

## 2. Ishga tushirish (30 soniya)

```bash
cd 02-Loyiha2-Trash-Organizer/MVP
set -a; . /home/user/.secrets/minds_keys.env; set +a
export ECO_API=http://127.0.0.1:8000 ECO_BOT_TOKEN="$TELEGRAM_BOT_TOKEN_ECO"
make serve &                      # API + xarita (:8000)
python3 -u scripts/bot.py         # bot (polling)
bash scripts/bot_healthcheck.sh   # 4 nuqtali tekshiruv
```

Docker varianti: `ECO_BOT_TOKEN=... docker compose --profile bot up -d` (API va bot birgalikda).

## 3. Push (fonda) — keyingi qadam

`due_events` natijalari har soatda tekshiriladi (cron/APScheduler): 7-kun ogohlantirish,
10-kun «muddati o'tdi», 15-kun eskalatsiya. Xabar matni `src/llm/generate.py` orqali —
**raqam registrdan, matn shablondan** (6 qavat verifikatsiya, V1–V6).

## 4. Xavfsizlik

- Token faqat `.secrets/minds_keys.env` da (huquq 600); kodda token yo'q.
- Token oshkor bo'lsa — @BotFather → `/revoke`, keyin qayta ishga tushirish.
- O'chirish endpointi yo'q — `service.delete()` `PermissionError` beradi (append-only audit).
- Telefon tasdiqlash 4 xonali kod; bir telefon → kuniga ≤5 murojaat (anti-spam).

## 5. Testlar

`tests/test_bot.py` — **16 test** (mock rejim, tokentsiz ishlaydi): buyruqlar menyusi, `/holat`
404 va muvaffaqiyat, `/xarita` ko'k-qoidasi, `/sla` paneli, `/kuzatish` zanjiri, FSM (qisqa tavsif
rad etilishi, lokatsiya qadami, dublikat javobi, API xatosi), payload shartnomasi.
Umumiy: `pytest -q tests/` → **141 test**.
