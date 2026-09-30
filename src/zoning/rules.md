# Zona qoidalari — inson tilida (TZ §5 ning to'liq nusxasi)

> Bu fayl — `engine.py` dagi kodning inson o'qiy oladigan shartnomasi.
> Har bir qoida o'zgarsa, `rule_version` ko'tariladi va eski natijalar **qayta yozilmaydi** (audit).

## 1. Asosiy rang (R = o'lchov / norma)

| Rang | Shart | Ma'nosi |
|---|---|---|
| 🔴 Qizil | R ≥ 2,0 | Normadan 2 baravar va undan ko'p oshgan |
| 🟡 Sariq | 1,0 < R < 2,0 | Oshgan, lekin 2 baravardan kam |
| 🟢 Yashil | R ≤ 1,0 **va** C ≥ 0,5 | Norma ichida, ishonchli ma'lumot bilan |
| 🔵 Ko'k-neytral | C < 0,5 **yoki** ma'lumot yo'q | *Ma'lumot yo'q — "toza" degani EMAS* |

**Ko'k zona** — alohida holat: u kamchilikni **ko'rsatadi** (e'lon qilmaydigan korxona "toza" ko'rinib qolmasligi kerak). Uning ulushi alohida KPI.

## 2. Ishonch darajasi (C) — ikkinchi o'q

`C = 0,30·f_recency + 0,25·f_redundancy + 0,25·f_method + 0,20·f_completeness`

- `f_recency`: ≤7 kun — 1,0 | ≤30 — 0,7 | ≤90 — 0,3 | >90 — 0
- `f_redundancy`: `min(1, manbalar/3)` — 3 mustaqil manba = to'liq ishonch
- `f_method`: akkreditatsiyalangan avtomatik — 1,0 | yarim avtomatik — 0,7 | self-report — 0,4 | fuqaro signali — 0,2
- `f_completeness`: mavjud indikatorlar / rejaviy indikatorlar

**Qoida:** yuqori oshib ketish + past ishonch → rang **ko'k** bo'lib qoladi, «tekshiruv kutilmoqda» belgisi bilan (sariq shtrix).

## 3. Kuchaytiruvchi qoidalar (override)

| # | Qoida | Natija |
|---|---|---|
| O1 | 2+ indikatorda R > 1 | rang bir pog'ona yuqoriga (yashil→sariq, sariq→qizil) |
| O2 | Tasdiqlangan murojaat | kamida sariq (qizil bo'lsa qoladi) |
| O3 | R ≥ 5 | qizil + birinchi navbatda tekshiruv |
| O4 | 3 yil ketma-ket shu oyda R>2 | «tizimli (mavsumiy)» bayrog'i — matnda ayblov emas |
| O5 | Tabiiy manba (chang bo'roni) | rang saqlanadi, izohga sabab qo'shiladi (yashilga o'tkazilmaydi) |
| O6 | Stansiya sanoat zonasidan uzoq | C −0,2 |

## 4. Severity (barcha §5 qoidalari uchun)

| Daraja | Mezon |
|---|---|
| 1 | R ≤ 2 (chegara atrofidagi tebranish) |
| 2 | 2 < R ≤ 5 (sezilarli oshib ketish) |
| 3 | R > 5 (ekstremal) |

## 5. Zona agregatsiyasi (§5.5)

```
RED    agar (RED va C≥0,5 va severity≥2) yoki (≥2 korxona sariq)
YELLOW agar (birorta sariq) yoki (red mavjud, lekin hammasi C<0,5)
GREEN  agar barcha monitoring qilingan obyektlar yashil VA qamrov ≥70%
BLUE   aks holda (jumladan: qamrov < 70%)
```

**Qamrov** har doim xaritada ochiq: "Yunusobod: 12/31 obyekt monitoringda — 39%".

## 6. Audit

- Har bir klass `facility_classes` jadvalida **tarix** sifatida saqlanadi; rang o'zgarishi `events`ga tushadi.
- `rule_version` o'zgarsa, eski snapshot'lar saqlanadi (qoida qayta yozilmaydi — faqat oldinga qo'llanadi).
