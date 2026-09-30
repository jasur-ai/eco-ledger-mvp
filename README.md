# OCHIQ-EKO-LEDGER MVP — ishlaydigan prototip

> Bu papka — **TZ (`../TZ/Loyiha2_Ochiq_Eko_Ledger_MVP_TZ.md`) bo'yicha S0–S7 bosqichlarning bajarilgan prototipi**.
> Har bir fayl TZ'dagi tegishli bosqichning "Deliverable" ustuniga mos keladi.

## Ishga tushirish (0 ta tashqi servis kerak)

```bash
cd MVP
make install                            # fastapi, uvicorn, pytest (+httpx)
make demo                               # DB seed + zona hisobi + hisobot + xarita
make test                               # 125 test
make serve                              # API (docs: /docs) — / da xarita
make bot                                # jonli bot (token: .secrets/minds_keys.env)
bash scripts/bot_healthcheck.sh         # 4 nuqtali salomatlik tekshiruvi
make docker                             # api + (profil) bot
```

## Bosqichlar ↔ fayllar xaritasi (TZ §3)

| Bosqich | TZ'dagi deliverable | Bu papkadagi holat |
|---|---|---|
| **S0** Ma'lumot modeli va manba tanlash | korxona kartochkasi, 3 indikator, 5 oqim kartografiyasi | `db/schema_sqlite.sql`, `db/schema_postgis.sql`, `src/seed.py` |
| **S1** Backend va baza | API + migratsiyalar + seed + 15 test | `src/db.py`, `src/api/app.py`, `tests/` |
| **S2** Zona-rang algoritmi | `zoning/engine.py` + `zoning/rules.md` + 100 test | ✅ `src/zoning/engine.py`, `src/zoning/rules.md`, `tests/test_zoning.py` |
| **S3** Xarita va dashboard | `web/map.html`, mobil moslashuv | ✅ `web/map.html` (o'z-o'zini o'zi ta'minlaydigan, tashqi CDN yo'q) |
| **S4** LLM matn generatori | `llm/prompt_v1.md`, `llm/verify.py`, 100 test-matn | ✅ `src/llm/generate.py`, `src/llm/prompt_v1.md` (deterministik shablon + 6 qavat verifikatsiya; API kaliti bo'lmasa ham ishlaydi) |
| **S5** Telegram bot | aiogram bot, 6 ssenariy | ✅ **jonli ishlayapti: [@ecoledg_bot](https://t.me/ecoledg_bot)** — `scripts/bot.py`, 4 qadamli FSM, lokatsiya, dublikat javobi; qo'llanma `docs/BOT-ISHLATISH.md` |
| **S6** Murojaat moduli | 7 holat, SLA, 25+ test | ✅ `src/murojaat/service.py`, `tests/test_murojaat.py` |
| **S7** Test/demo/hujjat | CI, demo, hisobot | ✅ `tests/` (**141** — 16 tasi bot handlerlari) · `Dockerfile` · `docker-compose.yml` · `.github/workflows/ci.yml` · `docs/architecture.md` · `docs/limitations.md` · `docs/DEMO-SSENARIYLAR.md` |

## Nima ishlaydi (haqiqiy natijalar)

- **Zona dvigateli:** R = o'lchov/norma → 4 rang (qizil/sariq/yashil/ko'k-neytral), C ishonch o'qi (w = 0,30/0,25/0,25/0,20), O1–O6 override qoidalari, severity 1–3 — TZ §5.1–§5.5 bilan 1:1.
- **Murojaat moduli:** 7 holatli zanjir, 10 ish kuni SLA (jurnalist — 5), 7/10/15-kun hodisalari, dublikat (ikki pog'onali trigramma), anti-spam (≤5/kun), o'chirish **yo'q** (append-only auditi).
- **LLM qatlami:** raqam registrdan olinadi, matn faqat izohlaydi; 6 qavat verifikatsiya (V1–V6) har matnga yozuv beradi.
- **API:** `/v1/geo/zones.geojson`, `/v1/export/measurements.csv`, `/v1/appeals`, `/v1/kpi/sla` — hammasi ochiq (Aarhus 4-modda + PRTR talabi).

## Bog'liqlik

`requirements.txt` — faqat `fastapi`, `uvicorn`, `pytest`, `httpx`. PostGIS varianti (`db/schema_postgis.sql`) real deploy uchun; demo SQLite'da ishlaydi (TZ §7.2 "MVP: 1 server" mantiqi).
