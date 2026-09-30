#!/usr/bin/env bash
# Bot va API salomatligini tekshirish (cron/systemd timer uchun tayyor)
# Foydalanish:  bash scripts/bot_healthcheck.sh
set -uo pipefail

ENVF="/home/user/.secrets/minds_keys.env"
[ -f "$ENVF" ] && set -a && . "$ENVF" && set +a

API="${ECO_API:-http://127.0.0.1:8000}"
TOKEN="${ECO_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN_ECO:-}}"
ok=0

echo "1) API (:8000) …"
if curl -s -m 5 "$API/v1/health" | grep -q '"status":"ok"'; then
  echo "   ✅ API javob beradi: $(curl -s -m 5 "$API/v1/health")"
else
  echo "   ❌ API javob bermayapti — 'make serve' yoki uvicorn qayta ishga tushiring"; ok=1
fi

echo "2) Zona qatlami …"
curl -s -m 5 "$API/v1/geo/zones.geojson" | grep -q '"features"' \
  && echo "   ✅ GeoJSON bor" || { echo "   ❌ GeoJSON yo'q"; ok=1; }

echo "3) Telegram bot …"
if [ -z "$TOKEN" ]; then
  echo "   ⚠️  token topilmadi (.secrets/minds_keys.env)"; ok=1
else
  R=$(curl -s -m 10 "https://api.telegram.org/bot${TOKEN}/getMe")
  echo "$R" | grep -q '"ok":true' && echo "   ✅ $(echo "$R" | python3 -c 'import json,sys;r=json.load(sys.stdin)["result"];print("@"+r["username"]+" ("+r["first_name"]+")")')" \
    || { echo "   ❌ getMe xatosi: $R"; ok=1; }
  W=$(curl -s -m 10 "https://api.telegram.org/bot${TOKEN}/getWebhookInfo")
  echo "$W" | python3 -c 'import json,sys;d=json.load(sys.stdin)["result"];print("   ℹ️  webhook:", repr(d.get("url")), "| kutilayotgan xabar:", d.get("pending_update_count"))'
fi

echo "4) Bot jarayoni …"
pgrep -af "scripts/bot.py" >/dev/null && echo "   ✅ bot.py ishlayapti (pid: $(pgrep -f 'scripts/bot.py' | tr '\n' ' '))" \
  || { echo "   ❌ bot.py jarayoni yo'q — qayta ishga tushiring:"; echo "      cd 02-Loyiha2-Trash-Organizer/MVP && ECO_BOT_TOKEN=\$TELEGRAM_BOT_TOKEN_ECO python3 -u scripts/bot.py"; ok=1; }

echo
[ "$ok" -eq 0 ] && echo "NATIJA: ✅ hammasi joyida" || echo "NATIJA: ❌ ba'zi tekshiruvlar yiqildi (yuqoriga qarang)"
exit "$ok"
