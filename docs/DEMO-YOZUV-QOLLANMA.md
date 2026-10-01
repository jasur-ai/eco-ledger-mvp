# Jonli video yozuv qo'llanmasi (4 video · ~8 daqiqa)

> **Repo nusxasi.** Ish muhitida bu qo'llanma `YAKUNIY/video/YOZUV-QOLLANMA.md` da turadi; yo'llar
> (`/home/user/…`, `YAKUNIY/video/`) ish muhitiga nisbatan — repo nusxasida `MVP/` papkasini shu papka deb o'qing.
>
> **Maqsad:** storyboard ([`DEMO-VIDEO-STORYBOARD.md`](DEMO-VIDEO-STORYBOARD.md))
> bo'yicha **ovozli, 1920×1080** versiyalarni bir o'tirishda yozib olish — qayta yozuvsiz.
> Avtomatik GIF nusxalar (`YAKUNIY/video/*.gif`, 4 ta) allaqachon bor: ular ovozsiz ko'rgazma
> varianti; bu qo'llanma esa **ovoz + tushuntirish** qo'shilgan asosiy versiyani yozish uchun.

---

## 0. Yozuvdan oldin (5 daqiqa)

```bash
bash /home/user/tools/record_preflight.sh     # 18 tekshiruv: xizmatlar, artefaktlar, sirlar
```

| Band | Nima uchun |
|---|---|
| Jonli xizmatlar | Videoda **haqiqiy** javob ko'rinishi kerak (API, GeoJSON, bot, scheduler) |
| Sahna artefaktlari | `eval_report.md`, `metadata.json`, `eco_ledger.db` — kadrda chiqadigan fayllar |
| Subtitr/kadr varaqlari | 4 `.srt` va 4 `.gif` joyidami (zaxira variant sifatida) |
| **Sir saqlash** | `.secrets/minds_keys.env` **yozuvda ekranga chiqmasligi shart** |

**Yozuv mashinasi talablari:** `ffmpeg` (yoki OBS Studio), 1920×1080 ekran, mikrofon.
Sandbox'da `ffmpeg` yo'q (root talab qiladi) — shuning uchun GIF'lar PIL orqali yasalgan; jonli yozuv
o'z kompyuteringizda quyidagi buyruqlar bilan bajariladi.

### Terminal va muhit sozlamalari

```bash
# 1) Sirlar tarixdan tozalanadi (yozuvda ↑ bosilganda chiqmasin)
history -c && export HISTFILE=/dev/null

# 2) Toza va barqaror ko'rinish
export PS1='\[\e[32m\]\w\[\e[0m\] $ '   # qisqa prompt
clear
reset                                   # katta o'lcham: Ctrl+Shift+= / terminal → 16-18pt
export LANG=uz_UZ.UTF-8 || export LANG=C.UTF-8   # µ, ³, — to'g'ri chiqishi uchun
```

**Shrift:** DejaVu Sans Mono **16–18pt** (monospace) · mavzu: qorong'i fon, oq matn ·
oyna 1920×1080, terminal to'liq ekranda (yoki o'ng 2/3 — brauzer bilan yonma-yon sahnada).

### Ovoz

| Sozlama | Qiymat |
|---|---|
| Mikrofon | tashqi, 20–30 sm, fon shovqini yo'q |
| Tekshiruv | 5 soniya yozib, tinglab ko'ring: «bir-ikki-uch, Ochiq-Eko-Ledger» |
| Bosh | har video boshida **1 soniya sukunat** (montaj uchun) |
| Temp | ~150 so'z/daqiqa — shoshilmang; raqam aytsangiz **ekranda o'sha raqam tursin** |

> **Fakt intizomi:** videoda aytilgan har bir son ekranda ko'rinishi shart. Raqamni yodda aytib,
> ekranda boshqa narsa ko'rsatish — ishonchni yo'qotadigan yagona narsa.
---

## 1. Video 1 — «Xarita va zona dvigateli» (2:10) · `demo-xarita.srt`

**Tayyorgarlik:** terminal toza · brauzerda 2 tab: `http://localhost:8000` (xarita) va
`http://localhost:8001/dashboard.html` (L1 panel — 4-videoda kerak).

| # | Vaqt | Ekran | Buyruq / harakat | Ekranda ko'rinadi (haqiqiy chiqish) | Ovoz (SRT matni) |
|---|---|---|---|---|---|
| 1 | 0:00–0:12 | Terminal | `cd ~/02-Loyiha2-Trash-Organizer/MVP && python3 scripts/run_demo.py 2>&1 \| head -4 \| cut -c1-104` | `Demo tayyor:` · `obyektlar: 78 \| zona ranglari: {…}` | «Ochiq-Eko-Ledger — ekologik ma'lumotni ochiq hisoblash tizimi…» |
| 2 | 0:12–0:30 | Terminal | `python3 /home/user/tools/demo_probe.py zones` | 6 tuman jadvali: `Yunusobod → red`, `Olmazor → blue` | «Diqqat: olti tumanda to'rt xil rang bor…» |
| 3 | 0:30–0:55 | Brauzer | `http://localhost:8000` — kursor **Olmazor** ustida | Xarita, legenda, 4 rang | «Ko'k — bu "toza" emas, "ma'lumot yo'q" degani. Olmazor qamrovi 46 foiz…» |
| 4 | 0:55–1:20 | Brauzer | Yunusobod → Chilonzor (rang va sabab) | Zona ranglari o'zgaradi | «Yunusobod qizil: R nisbati 6,2…» |
| 5 | 1:20–1:40 | Terminal | `python3 /home/user/tools/demo_probe.py api` | `HTTP 200 · FeatureCollection · obyektlar: 6` + zona jadvali | «Xuddi shu rang qatlami ochiq API orqali beriladi…» |
| 6 | 1:40–1:55 | Terminal | `python3 /home/user/tools/demo_probe.py lane` | `QOIDA 5.1 — rang chegaralari`, `Manba: SanQvaM 0053-23` | «Qoida ML emas, sof Python — chegaralar normadan kelib chiqadi…» |
| 7 | 1:55–2:10 | Terminal | `bash scripts/bot_healthcheck.sh` | `NATIJA: ✅ hammasi joyida` (4 nuqta) | «Yakuniy dalil: to'rt nuqtali salomatlik tekshiruvi — hammasi joyida.» |

> **Raqamlar izohi (yozuvdan oldin o'qib chiqing):** 78 obyekt · 6 tuman · 4 rang ·
> Olmazor 46% · 189 test. Bu sonlar `run_demo.py` va `zones` chiqishida **ko'rinadi** —
> aytilgan son ekranda bo'lishi shart.

**Zaxira kadr:** brauzer ochilmasa — `YAKUNIY/video/demo-xarita.gif` ni 3-sahna uchun ko'rsatib,
ovozni davom ettirish mumkin (ranglar bir xil).

---

## 2. Video 2 — «Murojaat: 7 holat va 10 kunlik SLA» (2:00) · `demo-murojaat.srt`

**Tayyorgarlik:** telefonda Telegram (admin akkaunt) · terminalda 2 tab (L2 papkasi) · brauzer tab.

| # | Vaqt | Ekran | Buyruq / harakat | Ekranda ko'rinadi | Ovoz |
|---|---|---|---|---|---|
| 1 | 0:00–0:15 | Telegram | `@ecoledg_bot` → `/murojaat` | Kategoriya tugmalari (7 ta) | «Murojaat to'rt qadamda qabul qilinadi…» |
| 2 | 0:15–0:40 | Telegram | Kategoriya → tavsif (30+ belgi) | `Tavsif juda qisqa` xatosi (ataylab) → qabul | «Tavsif qisqa bo'lsa qabul qilinmaydi — kamida 30 belgi…» |
| 3 | 0:40–1:00 | Telegram | Lokatsiya tugmasi → telefon | `Murojaat qabul qilindi: A-2026-…` | «Lokatsiya tugma bilan yuboriladi. Javob: murojaat kodi va muddat…» |
| 4 | 1:00–1:25 | Terminal | `python3 /home/user/tools/demo_probe.py dup` | `BIRLASHTIRILDI → A-2026-… · o'xshashlik 1.00 · qo'llab-quvvatlovchilar 2` | «Endi muhim qism: bir xil muammo qo'shni hovlidan ham keladi…» |
| 5 | 1:25–1:45 | Terminal | `python3 /home/user/tools/demo_probe.py sla` | Holat zanjiri (7) · `muddat 10 ish kuni` · hodisalar jadvali: `escalate` / `warn` / `overdue` | «Holat o'zgarganda hammasi tarixda qoladi… 7-kun / 10-kun / 15-kun» |
| 6 | 1:45–2:00 | Brauzer | `http://localhost:8000/v1/kpi/sla` | `"median_response_days": 4.0`, `"compliance_pct": 100.0` | «Xizmat ko'rsatish paneli ochiq: median javob 4 kun, muddatga rioya 100 foiz.» |

> **Sonlar dinamik:** `sla` probe'dagi hodisa yoshi (`age_days`) demo baza qayta yaratilganda o'zgaradi —
> shuning uchun ovozda aniq o'sha kunni aytmang, **«22 kun», «17 kun» o'rniga «20 kundan oshgan»** kabi
> barqaror ifoda ishlating. Median javob (4,0 kun) va rioya (100%) esa barqaror.
>
> **Ehtiyot:** `dup` probe **bazaning nusxasida** ishlaydi (asl `data/eco_ledger.db` daxlsiz) —
> shuning uchun yozuvdan keyin ham demo baza «iflos» bo'lmaydi.
> **Telegram dialogida admin chat ID ko'rinmasin**: 4-qadamni terminal orqali ko'rsatish shu uchun.

---

## 3. Video 3 — «LLM matn: raqam registrdan» (1:30) · `demo-llm.srt`

| # | Vaqt | Ekran | Buyruq / harakat | Ekranda ko'rinadi | Ovoz |
|---|---|---|---|---|---|
| 1 | 0:00–0:20 | Terminal | `python3 /home/user/tools/demo_probe.py llm` | `REGISTR YOZUVI` → `MATN (model: template-v1 · input hash …)` | «Bot e'lonni o'zi yozadi. Lekin qat'iy qoida bilan…» |
| 2 | 0:20–0:45 | Terminal | (o'sha chiqish pastga) | `VERIFIKATSIYA — 6 qavat` × `OK` → `HOLAT: PASS` | «Har matn olti qavat tekshiruvdan o'tadi: faktlar, raqamlar, taqiqlangan so'zlar, manba, format, namuna.» |
| 3 | 0:45–1:10 | Terminal | `python3 /home/user/tools/demo_probe.py llm-fail` | `HOLAT: FAIL:V3 → matn bloklandi` | «Sinab ko'ramiz: "Tavsiya: zavodni yopish kerak" qo'shsak — tizim matnni rad etadi.» |
| 4 | 1:10–1:30 | Terminal | `python3 -m pytest -q tests/test_llm.py \| tail -1` | `10 passed` | «O'n test bu qoidani qo'riqlaydi…» |

> **Diqqat:** LLM qatlami — **shablon + verifikatsiya**, erkin generatsiya emas. Bu farqni
> ovozda bir marta aytib o'ting (TZ §8.4 talabi).

---

## 4. Video 4 — «Model saralash: dreyf va FPR» (2:30) · `demo-model.srt`

| # | Vaqt | Ekran | Buyruq / harakat | Ekranda ko'rinadi | Ovoz |
|---|---|---|---|---|---|
| 1 | 0:00–0:25 | Terminal | `cd ~/01-Loyiha1-Carbon-Emission/MVP && python3 scripts/run_all.py \| tail -6` | Quvur ishlaydi (~23 s), `hisobot: reports/eval_report.md` | «Emissiya hisobotlaridagi anomaliyani topish. 50 600 yozuv…» |
| 2 | 0:25–0:50 | Terminal | `python3 /home/user/tools/demo_probe.py models` | Uch model jadvali: `IF … F1 0.5384 … FPR 0.0861` | «Isolation Forest: F1 0,538, soxta signallar ulushi 8,6 foiz — talab 10 foizdan past…» |
| 3 | 0:50–1:20 | Brauzer | `http://localhost:8001/dashboard.html` — KPI → alert feed | `E-GAZ-AUDIT — monitoring paneli`, top-20 ro'yxat | «Panel nima beradi: navbatdagi 20 shubhali hisobot va har biriga sabab…» |
| 4 | 1:20–1:50 | Brauzer | Panel pastga: **Model monitoring** | `drift_psi.png`, `fpr_trend.png` figuralari | «Bu — eng muhim qism: modelning o'zi ham nazorat qilinadi…» |
| 5 | 1:50–2:15 | Brauzer → Terminal | FPR trendi: 2026Q1 qatori → `python3 /home/user/tools/demo_probe.py digest` | `FPR chegaradan (0.10) oshgan davrlar: 2026Q1` · `QAROR: THRESHOLDNI QAYTA KALIBRLASH` | «Mana real topilma: 2026 birinchi choragida FPR chegaradan oshdi. Tizim shuni yashirmaydi…» |
| 6 | 2:15–2:30 | Terminal | `python3 -m pytest -q tests/ \| tail -1` | `54 passed` | «Yakun: 54 test yashil. Har da'vo test bilan qo'riqlanadi.» |

> **Ohang:** bu videoda halol chegara muhim — `QAROR: recalibrate` — **kamchilik emas, nazorat
> ishlayotganining dalili**. Aynan shu jumla bilan yakunlang.

---

## 5. Yozib olish (ffmpeg yoki OBS)

### Variant 0 — bir buyruq bilan (avtomatik, tavsiya etiladi)

```bash
bash scripts/record_all.sh --list         # ssenariylar va vaqtlar
bash scripts/record_all.sh --dry-run      # ffmpeg buyruqlari (yozmasdan ko'rish)
bash scripts/record_all.sh --demo model   # bitta video (subtitr kuydiriladi)
bash scripts/record_all.sh --all          # 4 tasi ketma-ket → YAKUNIY/video/live-<nom>.mp4
```

Sozlamalar bir joyda: `REC_SIZE` (1920x1080) · `REC_FPS` (30) · `REC_CRF` (20) · `REC_DISPLAY` (:0) —
skript boshidagi izohga qarang. Subtitr: `--subs burn|soft|none`.
**Talab:** ffmpeg + X11 · oldin `bash scripts/record_preflight.sh` (18 tekshiruv) ishga tushirilsin.
ⓘ Ovoz (mikrofon) avtomatik qo'shilmaydi — 4-video uchun ovozni qo'lda yozib, `ffmpeg -i live-<nom>.mp4 -i ovoz.wav -c:v copy -c:a aac …` bilan birlashtiring (yoki OBS'dan foydalaning, Variant B).

### Variant A — ffmpeg (Linux/X11)

```bash
cd ~/video-xom
# Ekran + mikrofon birga (x11grab + pulse). 1-video:
ffmpeg -f x11grab -video_size 1920x1080 -framerate 30 -i :0.0 \
       -f pulse -i default -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 128k \
       demo1-xom.mp4
# To'xtatish: q  (terminalda). Keyingi videolar: demo2-xom.mp4, demo3-xom.mp4, demo4-xom.mp4
```

### Variant B — OBS Studio

| Sozlama | Qiymat |
|---|---|
| Canvas / Output | 1920×1080 · 30 fps |
| Manbalar | 1) Display Capture 2) Audio Input Capture (mikrofon) |
| Recording | MP4 · CBR 6000 kbps yoki CRF 20 |
| Foydali | Har video boshida **1 s sukunat**; sahnalar orasida `Ctrl+Alt+R` bilan uzmasdan davom eting |

### Ovoz va rasm sifati tekshiruvi (yozuvdan keyin darhol)

```bash
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height \
        -of default=noprint_wrappers=1 demo1-xom.mp4
# kutilgan: h264 · 1920×1080 · ~130 s · audio bor
```

## 6. Montaj: subtitrni kuydirish va ovozni tekislash

```bash
# 1) Ovozni normallashtirish (-16 LUFS, YouTube standarti) va jimlikni boshdan kesish
ffmpeg -i demo1-xom.mp4 -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
       -c:v copy -c:a aac -b:a 160k demo1-norm.mp4

# 2) Subtitrni kuydirish (tayyor .srt — YAKUNIY/video/)
ffmpeg -i demo1-norm.mp4 -vf "subtitles=YAKUNIY/video/demo-xarita.srt:force_style='FontName=DejaVu Sans,FontSize=20,Outline=1'" \
       -c:a copy demo1-sub.mp4

# 3) Yakuniy eksport (web uchun)
ffmpeg -i demo1-sub.mp4 -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p \
       -movflags +faststart demo1-xarita-yakuniy.mp4
```

> `.srt` vaqtlari GIF versiyasidan: jonli yozuvda temp boshqacha bo'lsa, matnni **sahnalar bo'yicha**
> siljiting (`Subtitle Edit` yoki qo'lda) — so'zlar emas, **sahna vaqtlari** mos kelishi kerak.

## 7. Yozuvdan keyingi nazorat (majburiy)

| # | Tekshiruv | Qanday |
|---|---|---|
| 1 | Har aytilgan raqam ekranda ko'rindi | Videonu ko'rib chiqing: son ↔ kadr |
| 2 | Token / chat ID / parol kadrda yo'q | Kadrlarni 2× tezlikda ko'zdan kechiring; kerak bo'lsa **kadrni qayta yozing** |
| 3 | Xato (Traceback, `command not found`) ekranda yo'q | Har sahna oxirida **yashil ✅ yoki `passed`** ko'rinishi kerak |
| 4 | Ovoz balandligi bir xil | `loudnorm` barcha 4 videoga |
| 5 | Subtitr vaqtlari mos | Oxirgi 10 soniyada subtitr yo'q — yakun kadri ochiq ko'rinsin |
| 6 | Fayl nomi va joyi | `YAKUNIY/video/demo-<nom>-yakuniy.mp4` (4 ta) + `.srt` yonida |

## 8. Nashr variantlari

| Variant | Nima | Qayerga |
|---|---|---|
| **Ichki ko'rgazma** | 4 GIF (bor) | `YAKUNIY/video/` — taqdimot va hujjat ichida |
| **Jonli yozuv** (bu qo'llanma) | 4 MP4 + subtitr | `YAKUNIY/video/` + hisobot/taqdimotga havola |
| **Qisqa versiya** | 1 ta 90 soniyalik jamlanma (Video 1 + 4 dan eng muhim kadrlar) | Telegram kanal / e'lon |
| **Taqdimotda** | 20-slayd «Demo videolar» + GIF'lar jonli ko'rsatiladi | `YAKUNIY/00-MVP-TAQDIMOT.pptx` |

**Yakuniy kadr qoidasi (barcha videolarda):** oxirgi kadr — `pytest … passed` yoki
`bot_healthcheck.sh → NATIJA: ✅`. Bu «da'vo» emas, **ishlayotgan tizim dalili**.
