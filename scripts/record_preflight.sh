#!/usr/bin/env bash
# Yozuvga tayyorgarlik tekshiruvi (jonli video yozishdan OLDIN ishga tushiriladi).
# Ishlatish: bash scripts/record_preflight.sh     (MVP papkasidan yoki istalgan joydan)
# Har bir band: ✅/❌ + qisqa izoh. Yozuvda ekranga chiqadigan hamma narsa SHU YERDA sinovdan o'tadi.
set -u
# Yo'llar skript joyidan aniqlanadi (repo-safe): MVP/scripts/ → MVP/ → ish ildizi
HERE="$(cd "$(dirname "$0")/.." && pwd)"
L2="$HERE"
L1="${ECO_L1:-$HERE/../../01-Loyiha1-Carbon-Emission/MVP}"
VD="${ECO_VIDEO:-$HERE/../../YAKUNIY/video}"
SECRETS="${ECO_SECRETS:-$HERE/../../.secrets/minds_keys.env}"
ok=0; fail=0; warn=0
chk()  { printf "  %-42s %s\n" "$1" "$2"
         case "$2" in OK*) ok=$((ok+1));; *) fail=$((fail+1));; esac; }
warn_() { printf "  %-42s %s\n" "$1" "$2"; warn=$((warn+1)); }

echo "1) Jonli xizmatlar (yozuvda ko'rsatiladi)"
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 4 http://localhost:8000/v1/health || echo 000)
chk "API :8000 /v1/health" "$([ "$code" = "200" ] && echo OK || echo "$code")"
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 4 http://localhost:8001/ || echo 000)
chk "GeoJSON serveri :8001" "$([ "$code" = "200" ] && echo OK || echo "$code")"
pgrep -f "bot.py" >/dev/null && chk "bot.py jarayoni" OK || chk "bot.py jarayoni" YOQ
pgrep -f "sla_scheduler.py" >/dev/null && chk "sla_scheduler.py jarayoni" OK || chk "sla_scheduler.py jarayoni" YOQ

echo "2) Sahna artefaktlari (yozuvda ko'rinadi)"
[ -s "$L2/data/eco_ledger.db" ] && chk "L2 demo baza" OK || chk "L2 demo baza" YOQ
[ -s "$L1/reports/eval_report.md" ] && chk "L1 eval_report.md" OK || chk "L1 eval_report.md" YOQ
[ -s "$L1/models/metadata.json" ] && chk "L1 metadata.json" OK || chk "L1 metadata.json" YOQ

echo "3) Yozuv asboblari (yozuv paytida kerak — hozir yo'qligi ogohlantirish)"
command -v ffmpeg >/dev/null && chk "ffmpeg (video yozuv)" OK || warn_ "ffmpeg (video yozuv)" "YOQ — yozuv mashinasida o'rnating"
command -v python3 >/dev/null && chk "python3" OK || chk "python3" YOQ

echo "4) Subtitr va kadr varaqlari"
for d in xarita murojaat llm model; do
  [ -s "$VD/demo-$d.srt" ] && chk "demo-$d.srt" OK || chk "demo-$d.srt" YOQ
  [ -s "$VD/demo-$d.gif" ] && chk "demo-$d.gif" OK || chk "demo-$d.gif" YOQ
done

echo "5) Sir saqlash (yozuvda ekranga chiqmasligi SHART)"
if [ -f "$SECRETS" ]; then
  chk ".secrets/ mavjud (ekranga chiqarmang!)" OK
  leaks=$(grep -c 'AAH\|github_pat' "$HOME/.bash_history" 2>/dev/null || true)
  [ "${leaks:-0}" = "0" ] && chk "history'da token izi" "OK (0)" || chk "history'da token izi" "TOPILDI ($leaks) — tozalang"
else
  chk ".secrets/ topilmadi" YOQ
fi

echo
echo "NATIJA: $ok OK · $warn ogohlantirish · $fail muammo"
[ "$fail" -eq 0 ] && echo "Yozuvga tayyor ✅" || echo "Avval yuqoridagi muammolarni hal qiling."
exit 0
