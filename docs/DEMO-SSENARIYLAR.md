# S7 — 3 demo video stsenariysi (yozish uchun tayyor skriptlar)

> Har bir video 90–120 soniya. Terminal + brauzer ekran yozuvi (OBS/`ffmpeg`).

## Video 1 — «Xarita va zona dvigateli» (2 daqiqa)

```bash
cd 02-Loyiha2-Trash-Organizer/MVP && python3 scripts/run_demo.py && uvicorn src.api.app:app --port 8000
```
1. Brauzerda `http://localhost:8000` → xarita ochiladi.
2. Ko'rsatiladi: **🔴 Yunusobod** (R=6,2 ekstremal + O5 tabiiy manba), **🔴 Chilonzor** (2 sariq → agregatsiya),
   **🟡 M.Ulug'bek**, **🟢 Sergeli**, **🔵 Olmazor** (qamrov 46% — «toza emas»).
3. Legenda izohi: «ko'k = ma'lumot yo'q, toza degani emas».
4. `/v1/geo/zones.geojson` ochiladi — har zonada `coverage`, `rule_version`.
5. Yakun: `rule_version` va snapshot tamoyili (rang o'zgarsa — tarixda qoladi).

## Video 2 — «Murojaat: 7 holat va 10 kunlik SLA» (2 daqiqa)

```bash
python3 - <<'PY'
import sys; sys.path.insert(0,'.')
from src import db; from src.seed import seed, seed_appeals
from src.murojaat.service import AppealService
conn = db.connect(); seed(conn); codes, _ = seed_appeals(conn)
svc = AppealService(conn)
print("SLA:", svc.sla_report())
print("Hodisalar (7/10/15-kun):", svc.due_events())
a = svc.get(codes[4]); print("Zanjir:", [h["to_status"] for h in a["history"]])
try: svc.delete(codes[0])
except PermissionError as e: print("O'chirish rad etildi:", e)
PY
```
1. Bot oqimi (yoki API): murojaat → `yuborildi` → `ko'rib_chiqilmoqda` → javob → hal qilish (dalil bilan).
2. Rad etishda **sabab majburiy**; hal qilishda **tasdiq (o'lchov/foto) majburiy** — jonli ko'rsatiladi.
3. Dublikat: bir xil matn 100 m masofada → **birlashtirildi** (`supporters_count` oshadi, murojaat yo'qolmaydi).
4. `svc.delete()` → `PermissionError` (append-only).
5. `/v1/kpi/sla` — ochiq panel.

## Video 3 — «Jonli bot: @ecoledg_bot» (2 daqiqa)

> Jonli bot bor — video real Telegram'da yoziladi (ekran yozuvi).

1. `/start` — salomlashuv va 7 buyruq menyusi ko'rinadi.
2. `/xarita` — 6 zona rang emoji bilan, Olmazor «🔵 46% (toza emas!)» izohi.
3. `/holat E-1001` — rang, R, C, sabablar, JSST yorlig'i.
4. `/murojaat` — 4 qadam: kategoriya tugmasi → tavsif → **lokatsiya tugmasi** → telefon → kod olindi.
5. **Dublikat namoyishi:** ikkinchi qurilmadan o'xshash matn 100 m masofada → bot «birlashtirildi … yo'qolmadi,
   kuchini oshirdi» deb javob beradi.
6. `/kuzatish A-…` — zanjir va muddat; `/sla` — ochiq panel (median 4,0 kun, rioya 100%).
7. Yakun: `bash scripts/bot_healthcheck.sh` → 4 ✅ (operator ishonchi).

## Video 4 — «LLM matn: raqam registrdan, so'z shablondan» (90 soniya)

```bash
python3 - <<'PY'
import sys; sys.path.insert(0,'.')
from src.llm.generate import generate, render, verify
P = {"facility":"Sintetik obyekt-1","zone":"red","ratio":2.4,"value":84.0,"norm":35.0,
     "unit":"µg/m³","confidence":0.66,"reasons":["Normadan 2 baravar va undan ko'p oshgan: R=2.40"],
     "source":"gis.uznature.uz/stansiya-1204","updated_at":"2026-09-28"}
g = generate(P, "bot"); print(g["text"]); print("Verifikatsiya:", g["verify_status"], g["layers"])
# uydirma raqam urinishi:
bad = dict(P, reasons=["Tavsiya: zavodni yopish kerak"])
print("Buzilgan matn:", verify(render(bad,"bot"), bad, "bot")["status"])
PY
```
1. To'g'ri matn → **PASS** (V1–V6 yashil).
2. Raqam o'zgartirilsa yoki «tavsiya» qo'shilsa → **FAIL** (qaysi qavat ushlaganini ko'rsatish).
3. Xulosa: model e'lon qilishni tezlashtiradi, lekin faktni o'zgartirmaydi.
