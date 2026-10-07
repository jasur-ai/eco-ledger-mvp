# -*- coding: utf-8 -*-
"""S1/S3 — ochiq API (FastAPI). O'chirish endpoint'i ATAYLAB yo'q."""
from __future__ import annotations

import csv
import inspect
import io
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from .. import adolat, config, db
from ..llm.generate import generate
from ..murojaat.service import AppealError, AppealService
from ..zoning import engine

app = FastAPI(title="Ochiq-Eko-Ledger MVP", version="1.0",
              description="Zona-xaritasi va ochiq murojaat moduli (TZ S1–S7 prototipi)")


def get_conn():
    return db.connect()


def _kutilgan_maydonlar(metod) -> str:
    """Xizmat metodi qabul qiladigan maydonlar ro'yxati (400 xabari uchun)."""
    nomlar = [p.name for p in inspect.signature(metod).parameters.values() if p.name != "now"]
    return "So'rov maydonlari noto'g'ri. Qabul qilinadigan maydonlar: " + ", ".join(nomlar)


def _latest_classes(conn) -> dict:
    rows = conn.execute(
        "SELECT fc.*, f.zone_id, f.name FROM facility_classes fc JOIN facilities f USING(eco_id) "
        "WHERE fc.id IN (SELECT MAX(id) FROM facility_classes GROUP BY eco_id)").fetchall()
    return {r["eco_id"]: dict(r) for r in rows}


@app.get("/", include_in_schema=False)
def index():
    """Xarita (statik, o'z-o'zini ta'minlaydigan HTML)."""
    if os.path.exists(config.WEB_MAP):
        return FileResponse(config.WEB_MAP)
    return {"message": "Xarita hali yaratilmagan — `python3 scripts/run_demo.py` ishga tushiring"}


@app.get("/v1/health")
def health():
    c = get_conn()
    n = c.execute("SELECT COUNT(*) FROM facilities").fetchone()[0]
    return {"status": "ok", "facilities": n, "rule_version": engine.RULE_VERSION}


@app.get("/v1/geo/zones.geojson")
def zones_geojson():
    conn = get_conn()
    classes = _latest_classes(conn)
    feats = []
    for z in conn.execute("SELECT * FROM zones"):
        zid = z["zone_id"]
        facs = conn.execute("SELECT eco_id FROM facilities WHERE zone_id=?", (zid,)).fetchall()
        cls, measured = [], 0
        for fr in facs:
            c = classes.get(fr["eco_id"])
            if not c:
                continue
            payload_cls = {"zone": c["zone_class"], "severity": c["severity"], "C": c["confidence"],
                           "R": c["ratio"], "pending_review": False}
            cls.append(payload_cls)
            if c["ratio"] is not None:
                measured += 1
        coverage = measured / len(facs) if facs else 0.0
        color = engine.aggregate_zone(cls, coverage)
        d = 0.02
        poly = [[z["center_lon"] - d, z["center_lat"] - d], [z["center_lon"] + d, z["center_lat"] - d],
                [z["center_lon"] + d, z["center_lat"] + d], [z["center_lon"] - d, z["center_lat"] + d],
                [z["center_lon"] - d, z["center_lat"] - d]]
        feats.append({"type": "Feature",
                      "geometry": {"type": "Polygon", "coordinates": [poly]},
                      "properties": {"zone_id": zid, "name": z["name"], "zone_color": color,
                                     "facilities": len(facs), "measured": measured,
                                     "coverage": round(coverage, 3),
                                     "rule_version": engine.RULE_VERSION}})
    return {"type": "FeatureCollection", "features": feats}


@app.get("/v1/export/measurements.csv")
def export_csv():
    conn = get_conn()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["eco_id", "facility", "zone_id", "indicator", "value", "unit", "norm",
                "measured_at", "method", "n_sources", "source_ref"])
    q = """SELECT m.eco_id, f.name, f.zone_id, m.indicator, m.value, m.measured_at, m.method,
                  m.n_sources, m.source_ref FROM measurements m JOIN facilities f USING(eco_id)"""
    for r in conn.execute(q):
        unit = {"pm25": "µg/m³", "pm10": "µg/m³", "co": "mg/m³", "bod": "mgO₂/dm³", "kod": "mgO₂/dm³"}.get(r["indicator"], "")
        norm = 35.0 if r["indicator"] == "pm25" else (6.0 if r["indicator"] == "bod" else "")
        w.writerow([r["eco_id"], r["name"], r["zone_id"], r["indicator"], r["value"], unit, norm,
                    r["measured_at"], r["method"], r["n_sources"], r["source_ref"]])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=measurements.csv"})


@app.get("/v1/adolat/karta/{eco_id}")
def adolat_karta(eco_id: str, matn: bool = True):
    """Tushuntirish kartasi — 1C §C.2, 12 maydon (ma'lumot yo'q maydonlar «mavjud emas» deb ochiq yoziladi)."""
    conn = get_conn()
    try:
        card = adolat.explain_card(conn, eco_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from None
    if matn:
        card["etiroz_matni"] = {"uz": adolat.objection_text(card, "uz"),
                                "ru": adolat.objection_text(card, "ru")}
    return card


@app.get("/v1/adolat/karta/{eco_id}/html", response_class=HTMLResponse)
def adolat_karta_html(eco_id: str):
    """Chop etiladigan karta (A4, QR bilan) — brauzerda ochib PDF qilib saqlash mumkin."""
    conn = get_conn()
    try:
        return HTMLResponse(adolat.card_html(conn, eco_id))
    except ValueError as e:
        raise HTTPException(404, str(e)) from None


@app.get("/v1/adolat/hisobot")
def adolat_hisobot(chorak: str | None = None):
    """Choraklik «Aniqlik hisoboti» — 1C §E.2, 5 metrika (hisoblanmaydiganlari sabab bilan)."""
    return adolat.accuracy_report(get_conn(), quarter=chorak)


@app.get("/v1/adolat/oyna")
def adolat_oyna(qaror_sanasi: str):
    """Apellyatsiya oynasi: javob muddati (10 kun) va apellyatsiya oxiri (30 ish kuni)."""
    try:
        return adolat.appeal_window(qaror_sanasi)
    except ValueError:
        raise HTTPException(400, "Sana ISO ko'rinishida bo'lishi kerak (masalan 2026-09-25)") from None


@app.get("/v1/facilities/{eco_id}")
def facility_card(eco_id: str):
    conn = get_conn()
    f = conn.execute("SELECT * FROM facilities WHERE eco_id=?", (eco_id,)).fetchone()
    if not f:
        raise HTTPException(404, "Obyekt topilmadi")
    cls = conn.execute("SELECT * FROM facility_classes WHERE eco_id=? ORDER BY id DESC LIMIT 1",
                       (eco_id,)).fetchone()
    ms = [dict(m) for m in conn.execute("SELECT * FROM measurements WHERE eco_id=?", (eco_id,))]
    badges = []
    for m in ms:
        if m["indicator"] == "pm25" and m["value"]:
            badges.append({"type": "JSST etaloni", "value": config.WHO_PM25_ANNUAL, "unit": "µg/m³",
                           "ratio": round(m["value"] / config.WHO_PM25_ANNUAL, 2),
                           "note": "Sog'liq konteksti — rang berishda ishlatilmaydi (TZ §5.6)"})
    return {"facility": dict(f), "class": dict(cls) if cls else None,
            "reasons": json.loads(cls["reasons"]) if cls and cls["reasons"] else [],
            "measurements": ms, "badges": badges}


@app.post("/v1/appeals")
def create_appeal(body: dict):
    conn = get_conn()
    svc = AppealService(conn)
    try:
        return svc.create(**body)
    except AppealError as e:
        raise HTTPException(400, str(e))
    except TypeError:
        # noma'lum yoki yetishmayotgan maydon — 500 emas, tushunarli 400 (R58 tuzatishi)
        raise HTTPException(400, _kutilgan_maydonlar(svc.create)) from None


@app.get("/v1/appeals/due")
def due_appeals():
    """SLA nazorati: 7-kun ogohlantirish / muddati o'tgan / eskalatsiya (TZ §6.5)."""
    return {"due": AppealService(get_conn()).due_events()}


@app.post("/v1/bot/subscribe")
def bot_subscribe(body: dict):
    """Fuqaro chat'ini murojaatga obuna qilish (eslatmalar uchun)."""
    from src import notify
    try:
        return notify.subscribe(get_conn(), body.get("chat_id", 0), body.get("public_code", ""))
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/v1/bot/subscriptions")
def bot_subscriptions(chat_id: int):
    from src import notify
    return {"chat_id": chat_id, "codes": notify.subscriptions_of(get_conn(), chat_id)}


@app.get("/v1/appeals/{code}")
def get_appeal(code: str):
    conn = get_conn()
    try:
        return AppealService(conn).get(code)
    except AppealError as e:
        raise HTTPException(404, str(e))


@app.post("/v1/appeals/{code}/transitions")
def transition(code: str, body: dict):
    conn = get_conn()
    try:
        return AppealService(conn).transition(code, body.get("to_status", ""), body.get("actor", "system"),
                                              body.get("comment"), body.get("evidence"))
    except AppealError as e:
        raise HTTPException(400, str(e))


@app.get("/v1/kpi/sla")
def kpi():
    return AppealService(get_conn()).sla_report()


@app.get("/v1/bot/summary")
def bot_summary(eco_id: str | None = None):
    conn = get_conn()
    classes = _latest_classes(conn)
    if not classes:
        raise HTTPException(404, "Ma'lumot yo'q")
    if eco_id is None:
        eco_id = max(classes, key=lambda k: classes[k]["ratio"] or 0)
    c = classes[eco_id]
    payload = {"facility": c["name"], "zone": c["zone_class"], "ratio": c["ratio"],
               "value": None, "norm": 35.0, "unit": "µg/m³", "confidence": c["confidence"],
               "reasons": json.loads(c["reasons"] or "[]")[:2],
               "source": "gis.uznature.uz", "updated_at": c["computed_at"][:10]}
    m = conn.execute("SELECT value FROM measurements WHERE eco_id=? AND indicator='pm25'", (eco_id,)).fetchone()
    if m:
        payload["value"] = m["value"]
    return generate(payload, "bot")
