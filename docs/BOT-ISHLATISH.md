# Bot jonli ishlash qo'llanmasi (S5 — yakuniy)

**Bot:** [@ecoledg_bot](https://t.me/ecoledg_bot) («Ochiq-Eko-Ledger») · **Kod:** `scripts/bot.py` (aiogram 3)
**Holat:** ✅ **2026-09-30 dan jonli ishlayapti** (polling rejimi, API :8000 bilan).

## 1. Foydalanuvchi uchun (6 ssenariy)

| Buyruq | Nima qiladi |
|---|---|
| `/start` | salomlashuv + buyruqlar ro'yxati + «ko'k ≠ toza» qoidasi |
| `/holat E-1001` | obyekt: rang, R (nisbat), C (ishonch), sabablar (3 ta), JSST yorlig'i |
| `/xarita` | 6 zona: rang emoji, qamrov %, o'lchov/obyekt soni |
| `/murojaat` | 4 qadamli FSM: kategoriya (7 tugma) → tavsif (30–2000) → lokatsiya (tugma) → telefon → kod (masalan `A-2026-000001`) |
| `/kuzatish A-2026-000001` | holat zanjiri + SLA muddati + «yozuvlar o'chirilmaydi» izohi |
| `/sla` | ochiq panel: jami/ochiq, median javob (kun), rioya %, muddati o'tgan % |
| `/bekor` | joriy jarayonni to'xtatish |

Dublikat bo'lsa: bot **«murojaatingiz A-… bilan birlashtirildi (o'xshashlik 0,91, qo'llab-quvvatlovchilar 4) — yo'qolmadi, kuchini oshirdi»** deb javob beradi.

## 2. Ishga tushirish (operator uchun)

```bash
cd 02-Loyiha2-Trash-Organizer/MVP
set -a; . /home/user/.secrets/minds_keys.env; set +a      # tokenlar shu faylda (600 huquq)
export ECO_API=http://127.0.0.1:8000 ECO_BOT_TOKEN="$TELEGRAM_BOT_TOKEN_ECO"
make serve &            # 1) API + xarita (:8000)
python3 -u scripts/bot.py   # 2) bot (polling)
bash scripts/bot_healthcheck.sh   # 3) tekshiruv
```

Docker bilan: `ECO_BOT_TOKEN=... docker compose --profile bot up -d` (API + bot birgalikda).

## 3. Salomatlik tekshiruvi (`scripts/bot_healthcheck.sh`)

4 nuqtani tekshiradi: API `/v1/health` · GeoJSON qatlami · Telegram `getMe`/`getWebhookInfo` · `bot.py`
jarayoni. Cron bilan har 10 daqiqada:

```cron
*/10 * * * * cd /opt/eco-ledger/MVP && bash scripts/bot_healthcheck.sh >> /var/log/eco-bot.log 2>&1
```

## 3.1. Push-eslatmalar (7/10/15-kun) — jonli

`scripts/sla_scheduler.py` — SLA nazorati job'i (TZ §6.5):

| Kun | Hodisa | Kimga |
|---|---|---|
| 7 | `warn` — muddat yaqinlashdi | murojaat muallifi (bot obunasi) |
| 10+ | `overdue` — muddat o'tdi | muallif |
| 15+ | `escalate` — jiddiy kechikish | muallif **+ operator chat** (`ECO_ADMIN_CHAT_ID`) |

```bash
# doimiy rejim (30 daqiqada bir sikl)
export ECO_BOT_TOKEN="$TELEGRAM_BOT_TOKEN_ECO" ECO_ADMIN_CHAT_ID="$TELEGRAM_ADMIN_ID"
python3 -u scripts/sla_scheduler.py --interval 1800
# yoki cron: har soatda bir marta
# 0 * * * * cd /opt/eco-ledger/MVP && ECO_BOT_TOKEN=... python3 scripts/sla_scheduler.py --once
```

Tamoyillar (professional):
- **Dedupe:** bitta hodisa har bir chat uchun **bir marta** yuboriladi (`notification_log` jadvali) — spam yo'q.
  Yuborilmagan xabar jurnalga yozilmaydi → keyingi sikl qayta urinadi.
- **Admin takrori yo'q:** operator ham obunachi bo'lsa — bitta xabar (fuqaro matni ustuvor).
- **Shablon matn:** raqam faqat registrdan; taqiqlangan so'zlar testi bor (`ayblanadi/jarima/tavsiya` — yo'q).
- **Real yetkazish tasdiqlangan:** 2026-09-30 da 6 ta xabar Telegram'ga muvaffaqiyatli yuborildi (xato 0).
- **Testlar:** `tests/test_notify.py` — 17 test (matn, dedupe, admin eskalatsiyasi, obuna, API, xatoga chidamlilik).

## 4. Xavfsizlik va ekspluatatsiya izohlari

- **Token** faqat `.secrets/minds_keys.env` da (o'qish huquqi 600); kod ichida token yo'q —
  `scripts/bot.py` uni `ECO_BOT_TOKEN` muhit o'zgaruvchisidan oladi.
- Token oshkor bo'lsa: **@BotFather → /revoke** (bir zumda), keyin yangi token bilan qayta ishga tushirish.
- Bot **faqat API'ga** murojaat qiladi; DB'ga to'g'ridan-to'g'ri tegmaydi (yupqa klient printsipi).
- Xabar matnlarida shaxsiy ma'lumot ko'rsatilmaydi: kod (`A-2026-…`) va holat yetarli.
- Polling barqaror MVP uchun; katta yuklamada webhook tavsiya etiladi (keyingi bosqich).

## 5. Tekshirilgan holat (2026-09-30)

- `getMe` → @ecoledg_bot ✅ · `setMyCommands` → 7 buyruq ✅ · `setMyDescription` ✅
- Bot jarayoni ishga tushdi: `Bot ishga tushdi: @ecoledg_bot · API: http://127.0.0.1:8000` ✅
- API javoblari: `/v1/health` → 78 obyekt · `/v1/geo/zones.geojson` → 6 zona ✅
- `pytest -q tests/` → **189 test** (adolat 21 + murojaat 35 + bot 16 + push-eslatma 17 + qolgan 100) ✅
