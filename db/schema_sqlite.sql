-- OCHIQ-EKO-LEDGER MVP — ma'lumot modeli (TZ §4.3 + §6.6)
-- Bu fayl SQLite demo uchun. PostGIS varianti: schema_postgis.sql
-- Tamoyil: hech bir yozuv o'chirilmaydi; holat o'zgarishlari append-only jurnalga tushadi.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS norms (
  indicator   TEXT PRIMARY KEY,          -- 'pm25', 'pm10', 'co', 'bod', 'kod'
  kind        TEXT NOT NULL,             -- one_time | daily | annual | discharge
  value       REAL NOT NULL,
  unit        TEXT NOT NULL,
  basis       TEXT NOT NULL,             -- SanQvaM 0053-23, 26-son qoida, JSST
  valid_from  TEXT NOT NULL,
  note        TEXT
);

CREATE TABLE IF NOT EXISTS zones (
  zone_id     TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  center_lat  REAL NOT NULL,
  center_lon  REAL NOT NULL,
  area_km2    REAL
);

CREATE TABLE IF NOT EXISTS facilities (
  eco_id        TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  zone_id       TEXT REFERENCES zones(zone_id),
  lat           REAL NOT NULL,
  lon           REAL NOT NULL,
  sector        TEXT,
  station_far_from_industry INTEGER DEFAULT 0,   -- O6 uchun
  natural_source_flag        INTEGER DEFAULT 0,  -- O5 uchun (meteo tasdiq)
  seasonal_3y_flag           INTEGER DEFAULT 0,  -- O4 uchun
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS measurements (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  eco_id        TEXT NOT NULL REFERENCES facilities(eco_id),
  indicator     TEXT NOT NULL,
  value         REAL,
  measured_at   TEXT NOT NULL,
  method        TEXT NOT NULL,           -- auto_accredited | auto | semi | self_report | citizen
  n_sources     INTEGER NOT NULL DEFAULT 1,
  source_ref    TEXT
);

CREATE TABLE IF NOT EXISTS facility_classes (      -- tarix saqlanadi (TZ §4.3)
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  eco_id        TEXT NOT NULL REFERENCES facilities(eco_id),
  indicator     TEXT NOT NULL,
  ratio         REAL,                    -- R
  confidence    REAL,                    -- C
  zone_class    TEXT NOT NULL,           -- red | yellow | green | blue
  severity      INTEGER,
  rule_version  TEXT NOT NULL,
  reasons       TEXT,                    -- JSON
  computed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS zoning_runs (
  run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  scope         TEXT,
  rule_version  TEXT NOT NULL,
  input_hash    TEXT,
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  stats         TEXT                     -- JSON
);

CREATE TABLE IF NOT EXISTS events (       -- feed + bot push uchun
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  kind          TEXT NOT NULL,           -- class_change | spike | appeal_confirmed | sla_breach
  eco_id        TEXT,
  zone_id       TEXT,
  severity      INTEGER,
  payload       TEXT,
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appeals (
  appeal_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  public_code     TEXT UNIQUE NOT NULL,  -- A-2026-000123
  appeal_type     TEXT NOT NULL,         -- T1..T5
  category        TEXT NOT NULL,         -- air|water|waste|noise|odor|soil|other
  eco_id          TEXT REFERENCES facilities(eco_id),
  zone_id         TEXT REFERENCES zones(zone_id),
  lat             REAL NOT NULL,
  lon             REAL NOT NULL,
  description     TEXT NOT NULL,
  occurred_at     TEXT,
  status          TEXT NOT NULL,         -- 7 holat (§6.5)
  responsible_body TEXT,
  sla_deadline    TEXT NOT NULL,         -- +10 ish kuni (jurnalist +5 kun)
  first_response_at TEXT,
  resolved_at     TEXT,
  answer_text     TEXT,
  reject_reason   TEXT,
  author_phone    TEXT,                  -- tasdiqlangan telefon (anonimda NULL)
  author_kind     TEXT NOT NULL,         -- individual|legal|journalist|anonymous|facility
  publication_consent TEXT NOT NULL,     -- full_name|partial|anonymous
  report_to_authority INTEGER NOT NULL DEFAULT 1,
  lang            TEXT NOT NULL DEFAULT 'uz',
  supporters_count INTEGER NOT NULL DEFAULT 1,
  similar_group   TEXT,                  -- 0,55–0,85 o'xshashlik guruhi
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appeal_events (         -- append-only
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  appeal_id     INTEGER NOT NULL REFERENCES appeals(appeal_id),
  from_status   TEXT,
  to_status     TEXT NOT NULL,
  actor         TEXT NOT NULL,           -- citizen|system|operator
  comment       TEXT,
  evidence      TEXT,                    -- hal_qilindi uchun: o'lchov/foto havolasi
  ts            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sla_metrics (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  body          TEXT NOT NULL,           -- mas'ul organ
  period        TEXT NOT NULL,
  median_days   REAL,
  compliance_pct REAL,
  open_count    INTEGER,
  overdue_pct   REAL,
  computed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_texts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id      INTEGER,
  format        TEXT NOT NULL,           -- bot|press|weekly
  model         TEXT NOT NULL,           -- template-v1 | llm:<model>
  prompt_version TEXT,
  input_hash    TEXT,
  text          TEXT NOT NULL,
  verify_status TEXT NOT NULL,           -- PASS | FAIL:V1,V3 ...
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  entity        TEXT NOT NULL,
  entity_id     TEXT,
  action        TEXT NOT NULL,
  actor         TEXT,
  payload       TEXT,
  ts            TEXT NOT NULL
);

-- S6 qo'shimcha: push-eslatmalar (TZ §6.5) ---------------------------------
CREATE TABLE IF NOT EXISTS bot_subscriptions (
  chat_id     INTEGER NOT NULL,          -- fuqaro chat'i (bot)
  public_code TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (chat_id, public_code)
);

CREATE TABLE IF NOT EXISTS notification_log (   -- bitta hodisa bir marta yuboriladi
  event_key  TEXT PRIMARY KEY,
  code       TEXT,
  kind       TEXT,
  chat_id    INTEGER,
  sent_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
