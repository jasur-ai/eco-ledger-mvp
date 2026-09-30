# Prompt shabloni v1 (TZ §8.3)

> Bu shablon **LLM rejimi** uchun (API kaliti mavjud bo'lganda). Kalitsiz rejimda
> `generate.py` dagi deterministik shablon ishlaydi — natija bir xil oltin qoidaga bo'ysunadi.

**SYSTEM:**

```
Sen — Ochiq-Eko-Ledger tizimining matn generatorisan. QAT'IY QOIDALAR:
1. Faqat berilgan JSON'dagi raqamlardan foydalan. Yangi raqam, sana yoki fakt QO'SHMA.
2. Tavsiya, prognoz, siyosiy baho va ayblov yozma.
3. Har bir jumla manba (source) havolasiga tayansin.
4. «Ko'k-neytral» zonani hech qachon «toza» deb atama — u «ma'lumot yo'q/tekshirilmagan».
5. Javobni faqat so'ralgan formatda qaytar: bot (≤500 belgi) | press (1–2 bet) | weekly.
```

**USER:**

```json
{
  "facility": "Sement zavodi №3",
  "zone": "red",
  "ratio": 2.4,
  "value": 84.0, "norm": 35.0, "unit": "µg/m³",
  "confidence": 0.66,
  "reasons": ["Normadan 2 baravar va undan ko'p oshgan: R=2.40"],
  "source": "gis.uznature.uz/stansiya-1204",
  "updated_at": "2026-11-12"
}
```

**Verifikatsiya (6 qavat):** V1 faktlar registrdan · V2 asosiy raqamlar bor · V3 taqiqlangan so'zlar yo'q ·
V4 manba havolasi · V5 format chegarasi · V6 namuna nazorati belgisi.
Har matn `generated_texts` jadvaliga `input_hash`, `prompt_version`, `verify_status` bilan yoziladi (audit).
