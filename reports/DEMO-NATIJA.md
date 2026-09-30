# MVP demo natijasi (avtomatik hisobot)

**Sana:** 2026-09-28 09:00:00 · **rule_version:** 1.0 · **obyektlar:** 78

## 1. Zona ranglari (agregatsiya, TZ §5.5)

| Zona | Rang | Qamrov | Izoh |
|---|---|---|---|
| Yunusobod tumani | **red** | 16/16 (100%) | Qizil |
| Chilonzor tumani | **red** | 12/12 (100%) | Qizil |
| Mirzo Ulug'bek tumani | **yellow** | 12/12 (100%) | Sariq |
| Yakkasaroy tumani | **green** | 12/12 (100%) | Yashil |
| Olmazor tumani | **blue** | 6/13 (46%) | Ko'k-neytral |
| Sergeli tumani | **green** | 13/13 (100%) | Yashil |

Klass taqsimoti: red=4, yellow=4, green=62, blue=8 · «tekshiruv kutilmoqda» (ko'k+shtrix): 1

## 2. Maxsus holatlar (override qoidalari ishlaydi)

- **Sanoat parki obyekti №1 (sintetik)** (E-1001): R=6.2, C=0.9, rang=red, severity=3, override: O3
- **Sanoat parki obyekti №2 (sintetik)** (E-1002): R=2.4, C=0.373, rang=blue, severity=2
- **Sanoat parki obyekti №3 (sintetik)** (E-1003): R=1.4, C=0.917, rang=red, severity=1, override: O1
- **Sanoat parki obyekti №4 (sintetik)** (E-1004): R=0.8, C=0.817, rang=yellow, severity=1, override: O2
- **Sanoat parki obyekti №5 (sintetik)** (E-1005): R=3.1, C=0.9, rang=red, severity=2, override: O5
- **Sanoat parki obyekti №6 (sintetik)** (E-1006): R=2.2, C=0.9, rang=red, severity=2, override: O4
- **Chilonzor obyekti №1 (sintetik)** (E-2001): R=1.4, C=0.9, rang=yellow, severity=1
- **Chilonzor obyekti №2 (sintetik)** (E-2002): R=1.5, C=0.9, rang=yellow, severity=1
- **M.Ulug'bek obyekti №1 (sintetik)** (E-3001): R=1.5, C=0.817, rang=yellow, severity=1

## 3. Murojaat moduli (SLA, TZ §6.5)

- Yaratilgan murojaatlar: **8** (A-2026-000001, A-2026-000002, A-2026-000003, A-2026-000004, A-2026-000005, A-2026-000006, A-2026-000007, A-2026-000008)
- SLA hisoboti: median javob = 4.0 kun, muddatga rioya = 100.0%, ochiq = 5, muddati o'tgan = 1
- 7/10/15-kun hodisalari: [{"code": "A-2026-000004", "kind": "escalate", "age_days": 20.0}, {"code": "A-2026-000001", "kind": "overdue", "age_days": 15.0}, {"code": "A-2026-000002", "kind": "warn", "age_days": 8.0}]
- Dublikat birlashtirish: {"merged_into": "A-2026-000006", "similarity": 1.0, "supporters_count": 2}
- O'xshash guruh (0,55–0,85): G-d99700d7

## 4. Matn generatori (S4 — verifikatsiya)

- **bot** [PASS] · hash `12ebac5b5445e3ff`
  > Sanoat parki obyekti №1 (sintetik): holat — qizil zona. O'lchov 217.0 µg/m³, norma 35.0 µg/m³ (nisbat R=6.2). Ishonch darajasi C=0.9. Normadan 2 baravar va undan ko'p oshgan: R=6.20; O3: R ≥ 5 — birinchi navbatda tekshiruv Manba: gis.uznature.uz/stansiya-1001. Yangilandi: 2026-09-28.
- **bot** [PASS] · hash `1a895a1f401353a5`
  > Sanoat parki obyekti №5 (sintetik): holat — qizil zona. O'lchov 108.5 µg/m³, norma 35.0 µg/m³ (nisbat R=3.1). Ishonch darajasi C=0.9. Normadan 2 baravar va undan ko'p oshgan: R=3.10; O5: tabiiy manba (chang bo'roni/transchegaraviy) — rang saqlanadi, yashilga o'tkazilmaydi Manba: gis.uznature.uz/stansiya-1005. Yangilandi: 2026-09-28.
- **bot** [PASS] · hash `4f6aa40b057fb65b`
  > Sanoat parki obyekti №2 (sintetik): holat — ko'k-neytral zona. O'lchov 84.0 µg/m³, norma 35.0 µg/m³ (nisbat R=2.4). Ishonch darajasi C=0.373. Oshib ketish bor (R=2.40), lekin ishonch past (C=0.37) — rang ko'k, «tekshiruv kutilmoqda» shtrixi bilan Manba: gis.uznature.uz/stansiya-1002. Yangilandi: 2026-09-28.

## 5. Fayllar

- Xarita: `web/map.html` (o'z-o'zini ta'minlaydi, tashqi CDN yo'q)
- API: `uvicorn src.api.app:app` → `/v1/health`, `/v1/geo/zones.geojson`, `/v1/kpi/sla`
- CSV eksport: `data/measurements.csv` (ochiq ma'lumot talabi — Aarhus 4-modda)  
