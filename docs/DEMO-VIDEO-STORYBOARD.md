# Demo videolar — kadr-kadr storyboard (yozishga tayyor)

> **Tayyor nusxalar (4/4 — GIF avtomatik yozuv):** `YAKUNIY/video/` ichida `demo-xarita.gif` (Video 1 · 47,4 s),
> `demo-murojaat.gif` (Video 2 · 25,8 s), `demo-llm.gif` (Video 3 · 25,8 s), `demo-model.gif` (Video 4 · 45,4 s) —
> haqiqiy buyruq chiqishlaridan generatsiya qilingan; `.srt` subtitrlar va tekshiruv varaqlari yonida.
> Quyidagi jadval — **jonli ovozli yozuv** (2 daqiqali versiyalar) uchun kadr-kadr reja; GIF'lar o'sha rejaning
> qisqartirilgan, ovozsiz ko'rgazma nusxasi.
>
> 4 video · jami ~8 daqiqa · har bir kadr uchun: vaqt, ekran, harakat, **ovoz matni** (to'g'ridan-to'g'ri o'qish mumkin).
> Yozish asboblari: `ffmpeg` (Linux) yoki OBS. Subtitr: shu papkadagi `.srt` fayllar.
> Har video oxirida **jonli tekshiruv** ko'rsatiladi (`bot_healthcheck.sh` / `pytest`) — da'vo emas, dalil.

---

## Video 1 — «Xarita va zona dvigateli» (2:10) · subtitr: `demo1-xarita.srt`

| Vaqt | Ekran | Harakat | Ovoz matni |
|---|---|---|---|
| 0:00–0:12 | Terminal (katta shrift) | `python3 scripts/run_demo.py` — natija chiqadi | «Ochiq-Eko-Ledger — ekologik ma'lumotni ochiq hisoblash tizimi. Avval bazani va 78 obyektli demo o'lchovlarni tayyorlaymiz.» |
| 0:12–0:30 | Terminal natijasi | 4 ta zona rangi va klass taqsimoti ko'rinadi | «Diqqat: klass taqsimotida to'rt xil rang bor — qizil, sariq, yashil va ko'k. Ko'k — bu "toza" emas, "ma'lumot yo'q" degani.» |
| 0:30–0:55 | Brauzer: `localhost:8000` xarita | Kursor Olmazor tumanida | «Olmazor — ko'k zona: qamrov 46 foiz. Tizim bu yerda ataylab "yashil" demaydi: kam o'lchov bilan "toza" deyish — soxta ishonch bo'lardi.» |
| 0:55–1:20 | Brauzer: Yunusobod → Chilonzor | Tooltip: R=6,2 / 2 ta sariq korxona | «Yunusobod qizil: R nisbati 6,2, ya'ni normadan olti baravar oshgan. Chilonzor qizil: alohida sariq korxonalar birgalikda hududni qizilga chiqaradi — severity qoidasi shuni talab qiladi.» |
| 1:20–1:40 | Terminal | `curl -s localhost:8000/v1/geo/zones.geojson \| python3 -m json.tool \| head -30` | «Xuddi shu rang qatlami ochiq API orqali ham beriladi — har bir zonada qamrov koeffitsienti va qoida versiyasi ko'rinadi.» |
| 1:40–1:55 | Terminal | `ls src/zoning/` va `head -40 src/zoning/rules.md` | «Qoida ML emas, sof Python — har bir rangni fuqaro ham, sud ham tekshira oladi. Qoida versiyasi muzlatilgan: 1.0.» |
| 1:55–2:10 | Terminal | `bash scripts/bot_healthcheck.sh` | «Yakuniy dalil: to'rt nuqtali tekshiruv — API, zona qatlami, bot va jarayon holati. Hammasi joyida.» |

**Yozish buyruqlari:**
```bash
cd 02-Loyiha2-Trash-Organizer/MVP && python3 scripts/run_demo.py
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 &     # brauzer: http://localhost:8000
ffmpeg -f x11grab -video_size 1920x1080 -i :0.0 -f pulse -i default demo1.mp4   # audio bilan
ffmpeg -i demo1.mp4 -vf "subtitles=demo1-xarita.srt" demo1_sub.mp4              # subtitrni kuydirish
```

---

## Video 2 — «Murojaat: 7 holat va 10 kunlik SLA» (2:00)

| Vaqt | Ekran | Harakat | Ovoz matni |
|---|---|---|---|
| 0:00–0:15 | Telegram: @ecoledg_bot | `/murojaat` bosiladi | «Murojaat to'rt qadamda qabul qilinadi: kategoriya, tavsif, lokatsiya va telefon.» |
| 0:15–0:40 | Telegram | Kategoriya tanlanadi → tavsif yoziladi (30+ belgi) | «Tavsif qisqa bo'lsa qabul qilinmaydi — kamida 30 belgi. Bu operatorga emas, aynan sifat uchun talab.» |
| 0:40–1:00 | Telegram | Lokatsiya tugmasi → telefon → kod keladi | «Lokatsiya tugma bilan yuboriladi. Javob: murojaat kodi va muddat — joriy sanadan 10 ish kuni.» |
| 1:00–1:25 | Telegram | Ikkinchi qurilmadan o'xshash matn 100 m masofada | «Endi muhim qism: bir xil muammo qo'shni hovlidan ham keladi. Tizim uni alohida saqlamaydi — birlashtiradi va qo'llab-quvvatlovchilar sonini oshiradi. Murojaat yo'qolmaydi, kuchini oshiradi.» |
| 1:25–1:45 | Telegram | `/kuzatish` → holat zanjiri; `/eslatmalar` | «Holat o'zgarganda hammasi tarixda qoladi — o'chirish API darajasida taqiqlangan. 7-kun ogohlantirish, 10-kun muddati o'tdi, 15-kun eskalatsiya avtomatik ketadi.» |
| 1:45–2:00 | Brauzer: `/v1/kpi/sla` | JSON panel ko'rinadi | «Xizmat ko'rsatish paneli ochiq: median javob 4 kun, muddatga rioya 100 foiz. Ochig'i — ishonchning asosi.» |

---

## Video 3 — «LLM matn: raqam registrdan» (1:30)

| Vaqt | Ekran | Harakat | Ovoz matni |
|---|---|---|---|
| 0:00–0:20 | Terminal | `python3 - <<'PY'` (docs/DEMO-SSENARIYLAR.md, Video 4 skripti) → matn chop etiladi | «Bot e'lonni o'zi yozadi. Lekin qat'iy qoida bilan: barcha raqamlar registrdan, so'zlar shablondan.» |
| 0:20–0:45 | Terminal | Verifikatsiya natijasi: PASS, V1–V6 | «Har matn olti qavat tekshiruvdan o'tadi: faktlar, raqamlar, taqiqlangan so'zlar, manba, format va namuna.» |
| 0:45–1:10 | Terminal | Buzilgan matn: «Tavsiya: zavodni yopish kerak» → FAIL:V3 | «Sinab ko'ramiz: matnga "yopish kerak" degan gap qo'shsak — tizim matnni rad etadi. Model yozuvchi, hakam emas.» |
| 1:10–1:30 | Terminal | `pytest -q tests/test_llm.py` → 10 passed | «O'n test bu qoidani qo'riqlaydi: hech bir matn registrsiz raqam yoki taqiqlangan so'z bilan chiqmaydi.» |

---

## Video 4 — «Model saralash: 200 tekshiruvda 3,4 barobar» (2:30)

| Vaqt | Ekran | Harakat | Ovoz matni |
|---|---|---|---|
| 0:00–0:25 | Terminal | `make demo` (L1) → quvur ishlaydi | «Ikkinchi loyiha: emissiya hisobotlaridagi anomaliyani topish. 50 600 yozuv, 2 300 korxona.» |
| 0:25–0:50 | Terminal | Natija: IF F1 0,538 · FPR 0,086 | «Isolation Forest: F1 0,538, soxta signallar ulushi 8,6 foiz — talab 10 foizdan past, ya'ni bajarildi.» |
| 0:50–1:20 | Brauzer: dashboard | KPI kartalar → alert feed (top-20) | «Panel nima beradi: navbatdagi 20 shubhali hisobot va har biriga sabab — qaysi ko'rsatkich normadan qancha og'gan.» |
| 1:20–1:50 | Brauzer: dashboard pastga | «Model monitoring» bo'limi: PSI jadvali, FPR trendi | «Bu — eng muhim qism: modelning o'zi ham nazorat qilinadi. Feature dreyfi, skor dreyfi va davrlar kesimida FPR.» |
| 1:50–2:15 | Brauzer | 2026Q1 qatori qizil (FPR 0,126) | «Mana real topilma: 2026 birinchi choragida FPR chegaradan oshdi. Tizim shuni yashirmaydi — thresholdni qayta kalibrlashni tavsiya qiladi.» |
| 2:15–2:30 | Terminal | `make test` → 25 passed | «Yakun: 25 test yashil. Har da'vo test bilan qo'riqlanadi.» |

---

## Umumiy talablar (professional sifat)

- **Ekran:** 1920×1080, shrift ≥ 16pt, mavzu qorong'i (kontrast uchun).
- **Ovoz:** tashqi mikrofon, fon shovqinisiz; har video boshida 1 s sukunat.
- **Subtitr:** `.srt` fayllar shu hujjat yonida (`demo1-xarita.srt` na'munasi bor).
- **Fakt intizomi:** videoda aytilgan har raqam ekranda ko'rinishi shart (ko'r-ko'rona ovoz yo'q).
- **Yakuniy kadr:** `bot_healthcheck.sh` yoki `pytest` natijasi — ishlayotgan tizim dalili.
