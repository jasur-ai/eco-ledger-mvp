# -*- coding: utf-8 -*-
"""Yengil DB qatlami (SQLite). PostGIS varianti — db/schema_postgis.sql."""
import json
import os
import sqlite3
from . import config


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or config.DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    schema = os.path.join(config.BASE_DIR, "db", "schema_sqlite.sql")
    with open(schema, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


def audit(conn, entity, entity_id, action, actor="system", payload=None):
    conn.execute(
        "INSERT INTO audit_log(entity, entity_id, action, actor, payload, ts) "
        "VALUES (?,?,?,?,?, datetime('now'))",
        (entity, str(entity_id), action, actor, json.dumps(payload or {}, ensure_ascii=False)),
    )


def add_event(conn, kind, eco_id=None, zone_id=None, severity=None, payload=None, created_at=None):
    conn.execute(
        "INSERT INTO events(kind, eco_id, zone_id, severity, payload, created_at) "
        "VALUES (?,?,?,?,?, COALESCE(?, datetime('now')))",
        (kind, eco_id, zone_id, severity, json.dumps(payload or {}, ensure_ascii=False), created_at),
    )
