-- OCHIQ-EKO-LEDGER MVP — PostGIS varianti (real deploy, TZ §7.2)
-- Demo SQLite'da ishlaydi; bu fayl production sxemasi (TZ §4.3 + §6.6).

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE norms (
  indicator   TEXT PRIMARY KEY,
  kind        TEXT NOT NULL,
  value       NUMERIC NOT NULL,
  unit        TEXT NOT NULL,
  basis       TEXT NOT NULL,
  valid_from  DATE NOT NULL,
  note        TEXT
);

CREATE TABLE zones (
  zone_id     TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  geom        GEOMETRY(Polygon, 4326) NOT NULL,
  center      GEOMETRY(Point, 4326),
  area_km2    NUMERIC
);

CREATE TABLE facilities (
  eco_id      TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  zone_id     TEXT REFERENCES zones(zone_id),
  geom        GEOMETRY(Point, 4326) NOT NULL,
  sector      TEXT,
  station_far_from_industry BOOLEAN DEFAULT FALSE,
  natural_source_flag       BOOLEAN DEFAULT FALSE,
  seasonal_3y_flag          BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE measurements (
  id          BIGSERIAL PRIMARY KEY,
  eco_id      TEXT NOT NULL REFERENCES facilities(eco_id),
  indicator   TEXT NOT NULL REFERENCES norms(indicator),
  value       NUMERIC,
  measured_at TIMESTAMPTZ NOT NULL,
  method      TEXT NOT NULL CHECK (method IN ('auto_accredited','auto','semi','self_report','citizen')),
  n_sources   SMALLINT NOT NULL DEFAULT 1,
  source_ref  TEXT
);
CREATE INDEX measurements_eco_time ON measurements (eco_id, measured_at DESC);

CREATE TABLE facility_classes (
  id           BIGSERIAL PRIMARY KEY,
  eco_id       TEXT NOT NULL REFERENCES facilities(eco_id),
  indicator    TEXT NOT NULL,
  ratio        NUMERIC,
  confidence   NUMERIC,
  zone_class   TEXT NOT NULL CHECK (zone_class IN ('red','yellow','green','blue')),
  severity     SMALLINT,
  rule_version TEXT NOT NULL,
  reasons      JSONB,
  computed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX fc_eco_time ON facility_classes (eco_id, computed_at DESC);

CREATE TABLE zoning_runs (
  run_id       BIGSERIAL PRIMARY KEY,
  scope        TEXT,
  rule_version TEXT NOT NULL,
  input_hash   TEXT,
  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ,
  stats        JSONB
);

CREATE TABLE events (
  id         BIGSERIAL PRIMARY KEY,
  kind       TEXT NOT NULL CHECK (kind IN ('class_change','spike','appeal_confirmed','sla_breach')),
  eco_id     TEXT,
  zone_id    TEXT,
  severity   SMALLINT,
  payload    JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE appeals (
  appeal_id       BIGSERIAL PRIMARY KEY,
  public_code     TEXT UNIQUE NOT NULL,
  appeal_type     TEXT NOT NULL CHECK (appeal_type IN ('T1','T2','T3','T4','T5')),
  category        TEXT NOT NULL CHECK (category IN ('air','water','waste','noise','odor','soil','other')),
  eco_id          TEXT REFERENCES facilities(eco_id),
  zone_id         TEXT REFERENCES zones(zone_id),
  geom            GEOMETRY(Point, 4326) NOT NULL,
  description     TEXT NOT NULL CHECK (char_length(description) BETWEEN 30 AND 2000),
  occurred_at     TIMESTAMPTZ,
  status          TEXT NOT NULL CHECK (status IN ('yuborildi','ko''rib_chiqilmoqda','tashkilotga_yuborildi','javob_berildi','hal_qilindi','rad_etildi','apellyatsiya')),
  responsible_body TEXT,
  sla_deadline    TIMESTAMPTZ NOT NULL,
  first_response_at TIMESTAMPTZ,
  resolved_at     TIMESTAMPTZ,
  answer_text     TEXT,
  reject_reason   TEXT,
  author_phone    TEXT,
  author_kind     TEXT NOT NULL,
  publication_consent TEXT NOT NULL,
  report_to_authority BOOLEAN NOT NULL DEFAULT TRUE,
  lang            TEXT NOT NULL DEFAULT 'uz',
  supporters_count INTEGER NOT NULL DEFAULT 1,
  similar_group   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- O'chirish taqiqlangan: DELETE huquqi berilmaydi (append-only tamoyil, TZ §6.5)
REVOKE DELETE ON appeals, appeal_events, audit_log FROM PUBLIC;

CREATE TABLE appeal_events (
  id          BIGSERIAL PRIMARY KEY,
  appeal_id   BIGINT NOT NULL REFERENCES appeals(appeal_id),
  from_status TEXT,
  to_status   TEXT NOT NULL,
  actor       TEXT NOT NULL CHECK (actor IN ('citizen','system','operator')),
  comment     TEXT,
  evidence    TEXT,
  ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sla_metrics (
  id             BIGSERIAL PRIMARY KEY,
  body           TEXT NOT NULL,
  period         TEXT NOT NULL,
  median_days    NUMERIC,
  compliance_pct NUMERIC,
  open_count     INTEGER,
  overdue_pct    NUMERIC,
  computed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE generated_texts (
  id             BIGSERIAL PRIMARY KEY,
  event_id       BIGINT REFERENCES events(id),
  format         TEXT NOT NULL CHECK (format IN ('bot','press','weekly')),
  model          TEXT NOT NULL,
  prompt_version TEXT,
  input_hash     TEXT,
  text           TEXT NOT NULL,
  verify_status  TEXT NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
  id        BIGSERIAL PRIMARY KEY,
  entity    TEXT NOT NULL,
  entity_id TEXT,
  action    TEXT NOT NULL,
  actor     TEXT,
  payload   JSONB,
  ts        TIMESTAMPTZ NOT NULL DEFAULT now()
);
