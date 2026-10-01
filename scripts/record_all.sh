#!/usr/bin/env bash
# Jonli yozuv yordamchisi (4 ssenariy) — storyboard va subtitrlar asosida.
#
# Ishlatish:
#   bash tools/record_all.sh --list                    # ssenariylar va buyruqlar
#   bash tools/record_all.sh --dry-run                 # ffmpeg buyruqlarini chop etadi (yozmasdan)
#   bash tools/record_all.sh --demo xarita            # bitta ssenariyni yozadi
#   bash tools/record_all.sh --all                     # 4 tasini ketma-ket yozadi
#   bash tools/record_all.sh --demo model --subs burn  # subtitrni videoga kuydiradi
#   bash tools/record_all.sh --demo model --no-subs    # subtitrsiz
#
# Talablar: ffmpeg (x11grab bilan) · tayyorgarlik: `bash 02-…/MVP/scripts/record_preflight.sh` (18 tekshiruv)
# Chiqish: YAKUNIY/video/live-<demo>.mp4 (+ .srt nusxasi yonida)
#
# Nima uchun bu skript: YOZUV-QOLLANMA.md dagi qo'l bilan yozuv o'rniga — bir buyruq bilan,
# bir xil sozlamalar (o'lcham, fps, kodek, subtitr) va takrorlanadigan natija.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
# Skript ikki joyda yashaydi: ish ildizidagi tools/ va repo ichidagi MVP/scripts/.
# Shuning uchun ildiz aniqlanadi: yuqoriga qarab "01-… va 02-…" qardosh papkalari izlanadi.
find_root() {
  local d="$HERE"
  for _ in 1 2 3 4; do
    d="$(cd "$d/.." && pwd)"
    [ -d "$d/01-Loyiha1-Carbon-Emission" ] && [ -d "$d/02-Loyiha2-Trash-Organizer" ] && { echo "$d"; return; }
  done
  echo ""   # klon ichida (repo) — qardosh papkalar yo'q
}
WS="$(find_root)"
if [ -n "$WS" ]; then
  ROOT="$WS"; L1="$WS/01-Loyiha1-Carbon-Emission/MVP"; L2="$WS/02-Loyiha2-Trash-Organizer/MVP"; VD="$WS/YAKUNIY/video"
else
  L2="$(cd "$HERE/.." && pwd)"                      # repo ildizi = MVP
  ROOT="$(cd "$L2/.." && pwd)"
  L1="${ECO_L1:-}"                                  # klonda L1 yo'q — ECO_L1 bilan beriladi
  VD="${ECO_VIDEO:-$L2/docs/video}"                 # natija repo ichida (docs/video, yaratiladi)
fi
VD="${ECO_VIDEO:-$VD}"
L1="${ECO_L1:-$L1}"

# ---- yozuv sozlamalari (o'zgartirish shart bo'lsa — bir joyda) ----
DISP="${REC_DISPLAY:-:0}"          # X11 displey
SIZE="${REC_SIZE:-1920x1080}"      # yozib olish o'lchami
FPS="${REC_FPS:-30}"
CRF="${REC_CRF:-20}"               # sifat (kichik — yaxshi; 18–23 tavsiya)
PRESET="${REC_PRESET:-medium}"
OUTDIR="${REC_OUTDIR:-$VD}"

SUBS="burn"                        # burn | soft | none
ONLY_DEMO=""
DRY=0
LIST=0

usage() {
  sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --demo)   ONLY_DEMO="${2:-}"; shift 2 ;;
    --all)    ONLY_DEMO="all"; shift ;;
    --subs)   SUBS="${2:-burn}"; shift 2 ;;
    --no-subs) SUBS="none"; shift ;;
    --dry-run) DRY=1; shift ;;
    --list)   LIST=1; shift ;;
    -h|--help) usage ;;
    *) echo "nomalum argument: $1"; usage ;;
  esac
done

# ---- ssenariy ta'rifi: nom|ish papkasi|davomiylik (s)|nima ko'rsatiladi ----
# Davomiylik — storyboard dagi taxminiy vaqt (YOZUV-QOLLANMA.md §2–§5)
SCENARIOS=(
  "xarita|$L2|48|run_demo → zona jadvali → xarita (brauzer) → jonli GeoJSON API → norma chegaralari → healthcheck 4/4"
  "murojaat|$L2|26|holat zanjiri → SLA paneli (jonli API) → dublikat birlashtirish → append-only rad etish → 45 test"
  "llm|$L2|26|6 qavat verifikatsiya PASS → taqiqlangan gap FAIL:V3 → 10 test"
  "model|$L1|46|run_all → model jadvali → PR/ROC · PSI · FPR trendi → dayjest → 72 test"
)

demo_names() { for s in "${SCENARIOS[@]}"; do echo "${s%%|*}"; done; }

# L1 talab qilinadigan ssenariy (model) uchun tayyorgarlik xabari
if [ -z "$L1" ] || [ ! -d "$L1" ]; then
  warn_l1="⚠ L1 (01-Loyiha1-Carbon-Emission/MVP) topilmadi — «model» ssenariysi ishlamaydi.
   Klonda: ECO_L1=/yo'l/01-Loyiha1-Carbon-Emission/MVP bash scripts/record_all.sh --demo model"
else
  warn_l1=""
fi
scenario_line() { for s in "${SCENARIOS[@]}"; do [ "${s%%|*}" = "$1" ] && { echo "$s"; return; }; done; }

check_ffmpeg() {
  if ! command -v ffmpeg >/dev/null 2>&1; then
    cat <<'EOM'
❌ ffmpeg topilmadi — jonli yozuv uchun kerak.
   O'rnatish:
     • Debian/Ubuntu: sudo apt install -y ffmpeg
     • macOS (brew):  brew install ffmpeg
     • Windows:       winget install Gyan.FFmpeg
   ⓘ ffmpeg bo'lmasa ham GIF variantlar ishlaydi: python3 tools/make_demo_gif.py --demo <nom>
EOM
    return 1
  fi
  return 0
}

if [ "$LIST" = "1" ]; then
  echo "Yoziladigan ssenariylar (YAKUNIY/video/live-<nom>.mp4):"
  echo
  printf "  %-10s %-8s %s\n" "NOM" "VAQT" "NIMA KO'RSATILADI"
  for s in "${SCENARIOS[@]}"; do
    IFS='|' read -r n w d txt <<<"$s"
    printf "  %-10s %-8s %s\n" "$n" "${d}s" "$txt"
  done
  echo
  echo "Subtitr manbasi: $VD/demo-<nom>.srt · sozlama: --subs burn|soft|none"
  exit 0
fi

if [ "$DRY" = "1" ]; then
  command -v ffmpeg >/dev/null 2>&1 || echo "ⓘ eslatma: bu muhitda ffmpeg yo'q — quyidagi buyruqlar ffmpeg o'rnatilgan mashinada ishlaydi."
else
  check_ffmpeg || exit 2
fi

run_one() {
  local name="$1" workdir="$2" dur="$3" what="$4"
  local srt="$VD/demo-$name.srt"
  local sub_in="$VD/live-$name.srt"
  local out="$OUTDIR/live-$name.mp4"
  local src_args out_args

  echo "———————————————————————————————————————————————"
  echo "▶ $name — $what"
  if [ ! -d "$workdir" ]; then
    echo "  ❌ ish papkasi topilmadi: $workdir"
    [ -n "$warn_l1" ] && echo "$warn_l1"
    return 1
  fi
  echo "  ish papkasi: $workdir"

  # manba: x11grab (Linux) — boshqa OS da qo'lda yozuv: YOZUV-QOLLANMA.md §1
  src_args=(-f x11grab -framerate "$FPS" -video_size "$SIZE" -i "$DISP" -t "$dur")

  case "$SUBS" in
    burn)
      if [ -f "$srt" ]; then
        # srt ni yozuv papkasiga nisbiy yo'l bilan berish (ffmpeg escaping muammosiz)
        cp -f "$srt" "$sub_in"
        out_args=(-vf "subtitles=live-$name.srt:force_style='FontSize=22,Outline=2,Shadow=0'" \
                  -c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p -c:a aac -b:a 128k)
      else
        echo "  ⚠ $srt yo'q — subtitrsiz yoziladi"
        out_args=(-c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p -c:a aac -b:a 128k)
      fi ;;
    soft)
      out_args=(-c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p
                -i "$srt" -c:s mov_text -c:a aac -b:a 128k) ;;
    *)  out_args=(-c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p -c:a aac -b:a 128k) ;;
  esac

  if [ "$DRY" = "1" ]; then
    echo "  cd \"$workdir\""
    printf "  ffmpeg %s %s \"%s\"\n" "${src_args[*]}" "${out_args[*]}" "$out"
    [ "$SUBS" = "burn" ] && [ -f "$srt" ] && echo "  ⓘ subtitr kuydiriladi: $(basename "$srt") (FontSize=22, Outline=2)"
    return 0
  fi

  mkdir -p "$OUTDIR"
  ( cd "$workdir" && ffmpeg -hide_banner -y "${src_args[@]}" "${out_args[@]}" "$out" )
  local rc=$?
  if [ $rc -eq 0 ] && [ -f "$out" ]; then
    local mb; mb=$(awk "BEGIN{printf \"%.2f\", $(stat -c%s "$out" 2>/dev/null || stat -f%z "$out")/1048576}")
    echo "  ✅ yozildi: $out ($mb MB)"
    [ -f "$sub_in" ] && cp -f "$sub_in" "$OUTDIR/live-$name.srt"
    echo "  ⓘ ssenariy davomida: YOZUV-QOLLANMA.md §$( [ "$name" = xarita ] && echo 2 || ([ "$name" = murojaat ] && echo 3) || ([ "$name" = llm ] && echo 4) || echo 5 ) — buyruqlar shu tartibda bajariladi"
  else
    echo "  ❌ yozuv muvaffaqiyatsiz (ffmpeg kodi: $rc) — DISPLAY=$DISP to'g'rimi? (echo \$DISPLAY)"
    return 1
  fi
}

rc_all=0
if [ -z "$ONLY_DEMO" ]; then
  echo "Ishtatish: bash tools/record_all.sh --list | --all | --demo <nom> [--subs burn|soft|none] [--dry-run]"
  exit 1
fi

if [ "$ONLY_DEMO" = "all" ]; then
  for s in "${SCENARIOS[@]}"; do
    IFS='|' read -r n w d txt <<<"$s"
    run_one "$n" "$w" "$d" "$txt" || rc_all=1
  done
else
  line="$(scenario_line "$ONLY_DEMO")"
  if [ -z "$line" ]; then
    echo "❌ nomalum demo: $ONLY_DEMO — mavjud: $(demo_names | tr '\n' ' ')"
    exit 1
  fi
  IFS='|' read -r n w d txt <<<"$line"
  run_one "$n" "$w" "$d" "$txt" || rc_all=1
fi

echo "———————————————————————————————————————————————"
if [ "$DRY" = "1" ]; then
  echo "ℹ️  dry-run: hech narsa yozilmadi. Haqiqiy yozuv: --demo <nom> (ffmpeg va X11 kerak)"
else
  echo "Yakun. Yozuvlar: $OUTDIR/live-*.mp4 · subtitrlar: live-*.srt"
  echo "Keyingi qadam: kadrlarni tekshirish (ffmpeg -ss … -frames:v 1) va DEMO-YOZUV-QOLLANMA.md nazorat ro'yxati."
fi
exit $rc_all
