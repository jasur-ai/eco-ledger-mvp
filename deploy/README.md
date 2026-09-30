# Ishlab chiqarishga (production) ko'chirish qo'llanmasi

> **Maqsad:** Ochiq-Eko-Ledger (API + xarita + bot + SLA job) va E-GAZ-AUDIT (serving)
> ni VPS'da barqaror ishlatish. Sandbox'da hammasi tekshirilgan; bu hujjat — serverga ko'chirish tartibi.
>
> **Server talabi (MVP):** Ubuntu 22.04+ · 2 vCPU · 2 GB RAM · 20 GB disk · Docker 24+ · domen (ixtiyoriy, TLS uchun)

---

## 0. Nima qayerda ishlaydi

| Servis | Port | Rejim | Restart siyosati |
|---|---|---|---|
| `eco-api` (FastAPI + xarita) | 8000 | uvicorn, 2 worker | `unless-stopped` |
| `eco-bot` (aiogram polling) | — | bitta nusxa (polling!) | `unless-stopped` |
| `eco-scheduler` (7/10/15-kun) | — | har 30 daqiqada sikl | `unless-stopped` |
| `carbon-api` (L1 serving) | 8001 | uvicorn | `unless-stopped` |

⚠️ **Polling botni 2 nusxada ishga tushirmang** — Telegram `409 Conflict` beradi.
Kerak bo'lsa webhook rejimiga o'ting (pastda, §7).

---

## 1. Serverni tayyorlash

```bash
# 1) yangilanish va asosiy paketlar
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ufw sqlite3

# 2) Docker (rasmiy repodan)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
docker --version && docker compose version

# 3) fayerwall — faqat kerakli portlar
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp        # nginx/TLS uchun
# 8000/8001 ni TASHQARIGA OCHMANG — nginx orqali ochiladi
sudo ufw enable && sudo ufw status
```

## 2. Kodni joylash

```bash
sudo mkdir -p /opt/eco-ledger && sudo chown $USER /opt/eco-ledger
git clone https://github.com/jasur-ai/eco-ledger-mvp.git /opt/eco-ledger/MVP
git clone https://github.com/jasur-ai/egaz-audit-mvp.git  /opt/egaz-audit/MVP
```

## 3. Maxfiy sozlamalar (tokenlar)

```bash
cd /opt/eco-ledger/MVP
cp deploy/.env.example .env
chmod 600 .env
nano .env      # ECO_BOT_TOKEN, ECO_ADMIN_CHAT_ID, (ixtiyoriy) LLM kaliti
```

**Qoidalar:** `.env` hech qachon repoga tushmaydi (`.gitignore`da) · huquq `600` ·
token oshkor bo'lsa — @BotFather → `/revoke`, yangi token `.env` ga, `docker compose up -d`.

## 4. Ishga tushirish (Docker)

```bash
cd /opt/eco-ledger/MVP
docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
docker compose -f deploy/docker-compose.prod.yml ps
```

Tekshirish:

```bash
curl -s localhost:8000/v1/health        # {"status":"ok","facilities":78,...}
curl -s localhost:8000/v1/kpi/sla | head -c 200
docker compose -f deploy/docker-compose.prod.yml logs --tail=50 eco-bot
bash scripts/bot_healthcheck.sh
```

L1 (E-GAZ-AUDIT) birinchi ishga tushirish — model va ma'lumotni qayta qurish (~1 daqiqa):

```bash
cd /opt/egaz-audit/MVP
docker compose -f deploy/docker-compose.prod.yml run --rm carbon-api python3 scripts/run_all.py
docker compose -f deploy/docker-compose.prod.yml run --rm carbon-api python3 scripts/run_monitor.py
docker compose -f deploy/docker-compose.prod.yml up -d
```

## 5. Nginx + TLS (domen bilan)

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/eco-ledger
sudo ln -sf /etc/nginx/sites-available/eco-ledger /etc/nginx/sites-enabled/
sudo nano /etc/nginx/sites-available/eco-ledger     # server_name ni o'zgartiring
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d eco.example.uz              # TLS avtomatik
```

## 6. Zaxira nusxa (backup) — har kuni

```bash
chmod +x deploy/backup.sh
# cron: har kuni 03:15 da, 14 kun saqlanadi
( crontab -l 2>/dev/null; echo "15 3 * * * cd /opt/eco-ledger/MVP && ./deploy/backup.sh >> /var/log/eco-backup.log 2>&1" ) | crontab -
./deploy/backup.sh          # hoziroq sinash
```

Zaxira: `backups/eco_ledger_YYYYmmdd_HHMM.db.gz` · butunlik tekshiruvi bilan (`PRAGMA integrity_check`).
**Oflayn nusxa:** haftada bir marta `backups/` ni boshqa joyga (S3/rclone) ko'chirish tavsiya etiladi.

## 7. Ekspluatatsiya

| Vazifa | Buyruq |
|---|---|
| Loglar | `docker compose -f deploy/docker-compose.prod.yml logs -f --tail=100 eco-api` |
| Yangilash | `git pull && docker compose ... up -d --build` (bot ~5 s uziladi) |
| Qaytarish (rollback) | `git log --oneline -5` → `git checkout <commit>` → `up -d --build` |
| SLA jobni qo'lda sinash | `docker compose ... exec eco-scheduler python3 scripts/sla_scheduler.py --once` |
| Botni qo'lda sinash | `docker compose ... exec eco-bot python3 scripts/bot_healthcheck.sh` |
| Disk | `df -h` · zaxiralar 14 kun saqlanadi (~50 MB/oy) |

**Webhook rejimi (ixtiyoriy, ko'p yuklama uchun):** nginx'da `/tg/<secret>` → `eco-api:8000/webhook`,
`curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://eco.example.uz/tg/<secret>"`.
Polling nusxasini o'chirishni unutmang (§0 ogohlantirishi).

## 8. Xavfsizlik nazorati (har chorakda)

- [ ] Tokenlar `.env` da, `600`, repoda yo'q
- [ ] `docker compose ps` — faqat kerakli servislar ishlaydi
- [ ] `ufw status` — 8000/8001 tashqaridan yopiq
- [ ] Zaxira tiklab ko'rilgan (`gunzip -c backups/... | sqlite3 /tmp/test.db "PRAGMA integrity_check"`)
- [ ] `docker compose logs eco-bot | grep -c 409` → 0 (polling to'qnashuvi yo'q)

## 9. Muammolarni aniqlash (tez jadval)

| Alomat | Sabab | Yechim |
|---|---|---|
| Bot `409 Conflict` | ikki nusxa polling | ortiqcha konteynerni to'xtating: `docker compose ... stop eco-bot` |
| `chat not found` | foydalanuvchi `/start` bosmagan | foydalanuvchi botga kirishi kerak |
| API 502 (nginx) | konteyner ko'tarilmagan | `docker compose ps`, `logs eco-api` |
| SLA xabar kelmayapti | token yoki admin chat noto'g'ri | `docker compose ... exec eco-scheduler python3 scripts/sla_scheduler.py --once` |
| Xarita ochilmaydi | `web/map.html` yo'q | `docker compose ... exec eco-api python3 scripts/run_demo.py` |
