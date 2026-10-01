# 23 — LOYIHA 2 MVP TAYYORLIK HUKMI (OCHIQ-EKO-LEDGER) · **2026-10-01** (R54)

> # ✅ HA — LOYIHA 2 MVP TAYYOR
> **Ishlaydigan, testlangan, jonli so'rovlarga javob beradigan va chegaralari yozib qo'yilgan
> prototip.** Bu — «sanoat tizimi» degani emas: ma'lumot **sintetik** (real korxona nomi yo'q),
> baza **SQLite** (produksiya sxemasi PostGIS'da tayyor). Farq `docs/limitations.md` da ochiq.

---

## 1. Mezonlar — L1 bilan **bir xil** shkala

| Mezon | Holat | Dalil |
|---|---|---|
| **Ishlaydigan kod** | ✅ | 7 modul: `zoning` · `murojaat` · `adolat` · `notify` · `llm` · `bot` · `api` (`src/`) |
| **Testlar** | ✅ | **193** — `zoning` 79 · `murojaat` 35 · `adolat` 25 · `bot` 19 · `notify` 17 · `llm` 10 · `api` 8 |
| **CI (mustaqil klon)** | ✅ | `jasur-ai/eco-ledger-mvp` CI **#16 yashil** (commit `d05ac6a`) |
| **Jonli proba (bugun)** | ✅ | 7 endpoint **200**: `/v1/health` · `/v1/geo/zones.geojson` · `/v1/export/measurements.csv` · `/v1/adolat/karta/E-1001/html` · `/v1/adolat/hisobot` · `/v1/kpi/sla` · `/v1/bot/summary` |
| **Ma'lumot qatlami** | ✅ | `data/eco_ledger.db`: **78 obyekt · 73 o'lchov · 8 murojaat · 15 jadval** (audit izi: `events`, `appeal_events`, `audit_log`, `notification_log`) |
| **Qayta ishlab chiqarish** | ✅ | `make demo` (seed → zona → hisobot → xarita) · `pytest` · `uvicorn src.api.app:app` |
| **Bot** | ✅ **jonli** | `@ecoledg_bot` — `getMe` ✅ (id `8989725137`) · 4 qadamli FSM · 6 ssenariy · `docs/BOT-ISHLATISH.md` |
| **Deploy zaxirasi** | ✅ | `Dockerfile` · `docker-compose.prod.yml` · `nginx.conf` · `backup.sh` · `db/schema_postgis.sql` |
| **Halol chegara** | ✅ | `docs/limitations.md` — **7 band**, yashirilmagan (quyida §4) |

---

## 2. Nima qiladi (S0–S7)

| Qatlam | Nima | Jonli ko'rinish |
|---|---|---|
| **Zonalash** | 6 zona, **M1/M2 qoidasi bir xil emas** (ajratilmagan), o'lchov noaniqligi hisobga olinadi | `zones.geojson` — 6 zona, xossa: `facilities`, `measured`, `coverage` |
| **Ko'p qatlamli tekshiruv** | hisobotdagi raqamni 6 qavatdan o'tkazish (zona → mass-balans → dinamika) | `facility_classes` (qizil/sariq) |
| **Murojaat (SLA)** | holat mashinasi, `yakunlandi_tekshiruv` shu jumladan, 7/10/15 kun push-eslatmalar | `/v1/appeals/due` — jonli: **eskalatsiya 2 ta** |
| **Adolat paketi** | **12 maydonli** tushuntirish kartasi (5 tasi sabab bilan ochiq, «0» bilan yashirilmaydi) | `/v1/adolat/karta/E-1001/html` **200** |
| **Ochiq ma'lumot** | eksport: GeoJSON + CSV, audit izi bilan | `/v1/export/measurements.csv` **200** |
| **LLM/AI qatlami** | **6 qavatli verifikatsiya**, shablon rejimi kalitsiz ham ishlaydi | `/v1/bot/summary`: `template-v1`, `prompt v1`, `rule 1.0`, `input_hash` |

**Jonli KPI (bugun, `/v1/kpi/sla`):** jami **8** murojaat · javob berilgan **2** · ochiq **5** ·
muddati o'tgan **2** · o'rtacha javob **4,0 kun** · muddat bajarilishi **100%** · kechikish **40%**.
Ya'ni tizim faqat «ishlaydi» emas — **o'z SLA'sini o'lchab ko'rsatadi**.

---

## 3. Huquqiy bog'lanish (L2)

| Element | Asos |
|---|---|
| Murojaat va apellyatsiya muddatlari | **O'RQ-457** (30 ish kuni; 10/60 kun) + MJTK |
| Tushuntirish kartasi / «nega shunday qaror» | Konstitutsiya 49-modda · Aarhus (axborot + ishtirok) |
| Ochiq eksport (GeoJSON/CSV) | Ochiqlik qonuni (05.05.2014) |
| Zonalash va ustuvorlik | **PF-56 · PQ-184** (reestr tizimlari) — real oqim ochilganda ulanadi |
| Ishtirok va jamoatchilik nazorati | Aarhus 4–9-moddalar (paket: `APELLYATSIYA-PAKETI-1C-L2.md`) |

**Ochiq ish (keyingi qadam):** R54 huquqiy registri hozircha **L1 elementlarini** qoplaydi
(21 hujjat · 53 bog'lanish). **L2 elementlarini** shu registrga qo'shish — navbatdagi ish
(`huquqiy_asos.py` da L2 bo'limi).

---

## 4. Halol cheklovlar (`docs/limitations.md` + yangilanishlar)

| # | Cheklov | Holat |
|---|---|---|
| 1 | **Sintetik obyektlar** — real korxona nomlari ishlatilmaydi | ochiq (TZ §1 anti-da'vosi); real oqim: PF-56/PQ-184 ochilgach |
| 2 | **Bot tokeni** kerak edi | ✅ **yopildi (R53–R54)** — `@ecoledg_bot` jonli, `getMe` ✅ |
| 3 | **SQLite demo ↔ PostGIS produksiya** | sxema tayyor (`db/schema_postgis.sql`), ko'chirish kodda izohlangan |
| 4 | **Bayramlar hisobga olinmagan** — SLA faqat Sh/Ya tashlaydi | ochiq (ishlab chiqarishda bayram kalendari) |
| 5 | **Yuridik jihat** — natija dalil emas, «qizil» = ustuvor tekshiruv manzili | ochiq (anti-da'volar) |
| 6 | **LLM rejimi** — hozir deterministik shablon; kalit ulanganda ham **6 qavat verifikatsiya** o'zgarmaydi | ochiq |
| 7 | **Dioksin/kul indikatori** WtE uchun MVP'da yo'q | ochiq (Maqola 2 — tavsiya 12) |
| 8 | **L1 darajasidagi «o'lchov ishonchi» moduli** (kirishsiz tekshiruv) L2 da yo'q | ochiq — L1 modullarini L2 zonalashiga ulash mumkin (keyingi qadam) |

---

## 5. Imkoniyatdan kelib chiqqan yakuniy hukm

1. **Murojaat zanjiri to'liq ishlaydi** — yaratish → holatlar → SLA → push → yakuniy tekshiruv;
   muddatlar huquqiy hujjatga (O'RQ-457) bog'langan.
2. **Adolat paketi — eng kuchli qism:** 12 maydonli karta «0» bilan yashirmaydi, ochiq sabab yozadi;
   bu Aarhus ruhidagi «nega bunday qaror?» savoliga javob beradi.
3. **AI qatlami ehtiyotkor:** kaltissiz ham ishlaydi, har matnda model + prompt + qoida versiyasi va
   **kirish xeshi** saqlanadi (`generated_texts`) — takrorlanuvchanlik ta'minlangan.
4. **Chegara ochiq:** sintetik ma'lumot, SQLite, bayramsiz kalendar — uchtasi ham hujjatda.
   Shuning uchun bu «sanoat tizimi» emas, **ishlaydigan, ko'rsatiladigan va kengaytiriladigan MVP**.
5. **L1 bilan juftlik:** L1 «raqam ishonchli emas» ni isbotlaydi, L2 «keyin nima qilish kerak» ni
   ko'rsatadi — ikki loyiha bitta zanjirning ikki uchi.

**Xulosa: HA — Loyiha 2 MVP ham tayyor** (ishlaydigan prototip darajasida, chegaralari yozilgan).

---

## 6. Reproduksiya — uchta buyruq

```bash
cd 02-Loyiha2-Trash-Organizer/MVP
make demo                                       # DB seed + zona + hisobot + xarita
python3 -m pytest -q                            # 193 passed
uvicorn src.api.app:app --host 0.0.0.0 --port 8000   # API: /docs, /v1/kpi/sla, /v1/adolat/...
```

---

## 7. Keyingi qadam (ustuvorlik bo'yicha)

1. **L2 elementlarini huquqiy registrga qo'shish** (`huquqiy_asos.py`, PF-56 · PQ-184 · O'RQ-457).
2. **Bayram kalendari** (SLA aniqligi) — 4-cheklovni yopish.
3. **PostGIS ko'chirish** — sxema tayyor, demo → produksiya qadami.
4. **L1 ↔ L2 ulash**: L1 ning o'lchov ishonchi natijasini L2 zonalashiga kirish signali sifatida berish.
