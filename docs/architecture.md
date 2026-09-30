# Ochiq-Eko-Ledger — arxitektura (5 qatlam, TZ §7)

```
┌─ 1. Manba ──────────────┐  ┌─ 2. Ingestion ───────────┐  ┌─ 3. Yadro ─────────────────┐
│ PF-56 yagona hisob      │  │ measurements (o'lchovlar)│  │ zoning/engine.py           │
│ PQ-184 ochiq monitoring │─▶│ seed / API / bot         │─▶│ R = V/N · C ishonch        │
│ PQ-343 platforma        │  │ append-only audit_log    │  │ O1–O6 + severity 1–3       │
└─────────────────────────┘  └──────────────────────────┘  └────────────┬───────────────┘
                                                                        │
┌─ 5. Ishonch ────────────┐  ┌─ 4. E'lon (5 kanal) ─────┐  ┌───────────┴───────────────┐
│ murojaat moduli (7 holat│  │ rasmiy sayt · ochiq API  │  │ facility_classes (tarix)  │
│ SLA 10 kun · KPI ochiq) │◀─│ bot · matbuot · xarita   │◀─│ events · zoning_runs      │
│ audit (o'chirilmaydi)   │  │ LLM 6-qavat verifikatsiya│  │ rule_version snapshot     │
└─────────────────────────┘  └──────────────────────────┘  └───────────────────────────┘
```

## Fayl ↔ qatlam xaritasi

| Qatlam | Kod | TZ bo'limi |
|---|---|---|
| Ma'lumot modeli | `db/schema_sqlite.sql`, `db/schema_postgis.sql` | §4 |
| Yadro (zona) | `src/zoning/engine.py` + `rules.md` | §5 (1:1) |
| API | `src/api/app.py` | §7.1 |
| LLM | `src/llm/generate.py`, `prompt_v1.md` | §8 |
| Murojaat | `src/murojaat/service.py` | §6 |
| Bot | `scripts/bot.py` (aiogram 3) | §6.3 (asosiy kanal) |
| Demo/xarita | `scripts/run_demo.py` → `web/map.html` | §5.8 |

## Asosiy dizayn qarorlari

1. **Zona qoidasi sof Python, ML emas** (TZ S2): har bir rangni fuqaro va sud tekshira oladi;
   qoida versiyasi (`rule_version`) bilan muzlatiladi.
2. **«Ma'lumot yo'q» ≠ yashil:** ko'k-neytral alohida holat va alohida KPI (TZ §5.1).
3. **Severity agregatsiya:** chegara atrofidagi bitta o'lchov hududni qizil qilmaydi (severity≥2 sharti).
4. **Append-only:** `DELETE` taqiqlangan (DB huquqi + `service.delete()` xatosi) — ishonch audit izidan keladi.
5. **LLM yozuvchi, hakam emas:** matn faqat registr yozuvidan quriladi; 6 qavat verifikatsiya.

## Ishlab chiqish oqimi

```bash
make install   # pip install -r requirements.txt
make demo      # seed + hisob + hisobot + xarita
make test      # pytest -q tests/  (125 test)
make serve     # uvicorn src.api.app:app --port 8000  →  / da xarita
make bot       # ECO_BOT_TOKEN kerak (docs/BOT-INTEGRATSIYA.md)
make docker    # docker compose up --build (api + bot profili)
```
