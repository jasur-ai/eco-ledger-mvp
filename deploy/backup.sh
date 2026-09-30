#!/usr/bin/env bash
# Eko-Ledger bazasini zaxiralash (kunlik cron uchun).
#   ./deploy/backup.sh [saqlash_kunlari=14]
# Tamoyil: python sqlite3 .backup (ishlayotgan bazadan xavfsiz nusxa, WAL rejimida ham izchil)
#          → butunlik tekshiruvi → gzip → eski nusxalarni tozalash.
# python3 yetarli — sqlite3 CLI kerak emas.
set -euo pipefail

KEEP_DAYS="${1:-14}"
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$BASE/backups"
DB_PATH="${ECO_LEDGER_DB:-$BASE/data/eco_ledger.db}"
STAMP="$(date +%Y%m%d_%H%M%S)"
RAW="$BACKUP_DIR/eco_ledger_${STAMP}.db"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
  echo "❌ Baza topilmadi: $DB_PATH" >&2
  exit 1
fi

python3 - "$DB_PATH" "$RAW" <<'PY'
import os
import sqlite3
import sys

src, dst = sys.argv[1], sys.argv[2]
if os.path.exists(dst):
    os.remove(dst)
with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
    s.backup(d)                                   # xavfsiz onlayn nusxa
with sqlite3.connect(dst) as d:
    check = d.execute("PRAGMA integrity_check;").fetchone()[0]
    if check != "ok":
        raise SystemExit(f"integrity_check: {check}")
    n_fac = d.execute("SELECT COUNT(*) FROM facilities").fetchone()[0]
    n_app = d.execute("SELECT COUNT(*) FROM appeals").fetchone()[0]
print(f"  nusxa olindi: {n_fac} obyekt · {n_app} murojaat")
PY

if [ ! -f "$RAW" ]; then
  echo "❌ Nusxa yaratilmadi" >&2
  exit 2
fi

if ! gzip -f -9 "$RAW"; then
  rm -f "$RAW"
  echo "❌ Siqish yiqildi" >&2
  exit 3
fi

DELETED="$(find "$BACKUP_DIR" -name 'eco_ledger_*.db.gz' -mtime "+$KEEP_DAYS" -print -delete | wc -l)"
SIZE="$(du -h "$RAW.gz" | cut -f1)"
COUNT="$(find "$BACKUP_DIR" -name 'eco_ledger_*.db.gz' | wc -l)"
echo "✅ Zaxira: $(basename "$RAW").gz ($SIZE) · jami nusxa: $COUNT · tozalandi: $DELETED (${KEEP_DAYS} kundan eski)"
