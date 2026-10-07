# -*- coding: utf-8 -*-
"""S0/S1 — sintetik demo ma'lumotlar (real korxona nomlari YO'Q — TZ §1 anti-da'vosi)."""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from . import config, db
from .zoning import engine
from .zoning.engine import Indicator, compute_facility

RNG = random.Random(42)
NOW = datetime(2026, 9, 28, 9, 0, 0)

ZONES = [
    ("Z-YUN", "Yunusobod tumani", 41.355, 69.285, 39.0),
    ("Z-CHI", "Chilonzor tumani", 41.275, 69.205, 44.0),
    ("Z-MUL", "Mirzo Ulug'bek tumani", 41.325, 69.335, 36.0),
    ("Z-YAK", "Yakkasaroy tumani", 41.285, 69.265, 14.0),
    ("Z-OLM", "Olmazor tumani", 41.345, 69.215, 51.0),
    ("Z-SER", "Sergeli tumani", 41.220, 69.220, 66.0),
]

# maxsus holatlar: (eco_id, zona, nom, pm25_qiymat, usul, manba_soni, recency, bod, flaglar)
SPECIALS = {
    "E-1001": ("Z-YUN", "Sanoat parki obyekti №1 (sintetik)", 217.0, "auto_accredited", 3, 3, None, {}),
    "E-1002": ("Z-YUN", "Sanoat parki obyekti №2 (sintetik)", 84.0, "self_report", 1, 40, None, {}),
    "E-1003": ("Z-YUN", "Sanoat parki obyekti №3 (sintetik)", 45.5, "auto", 2, 5, 8.4, {}),
    "E-1004": ("Z-YUN", "Sanoat parki obyekti №4 (sintetik)", 28.0, "auto", 2, 6, None, {"appeal_confirmed": True}),
    "E-1005": ("Z-YUN", "Sanoat parki obyekti №5 (sintetik)", 108.5, "auto_accredited", 3, 4, None, {"natural_source": True}),
    "E-1006": ("Z-YUN", "Sanoat parki obyekti №6 (sintetik)", 77.0, "auto_accredited", 3, 6, None, {"seasonal_3y": True}),
    # Chilonzor — 2 sariq → zona RED (agregatsiya qoidasi)
    "E-2001": ("Z-CHI", "Chilonzor obyekti №1 (sintetik)", 49.0, "auto", 3, 5, None, {}),
    "E-2002": ("Z-CHI", "Chilonzor obyekti №2 (sintetik)", 52.5, "auto", 3, 5, None, {}),
    # Mirzo Ulug'bek — qizil bor, lekin C past (self-report) → zona YELLOW
    "E-3001": ("Z-MUL", "M.Ulug'bek obyekti №1 (sintetik)", 52.5, "auto", 2, 5, None, {}),
    "E-3002": ("Z-MUL", "M.Ulug'bek obyekti №2 (sintetik)", 21.0, "auto", 3, 4, None, {}),
    # Yakkasaroy — bitta sariq → zona YELLOW
    "E-4001": ("Z-YAK", "Yakkasaroy obyekti №1 (sintetik)", 30.8, "auto", 3, 5, None, {}),
    "E-4002": ("Z-YAK", "Yakkasaroy obyekti №2 (sintetik)", 24.5, "auto_accredited", 3, 3, None, {}),
    # Olmazor — qamrov past (6 dan 3 tasi o'lchovli) → zona BLUE
    "E-5001": ("Z-OLM", "Olmazor obyekti №1 (sintetik)", 26.25, "auto", 2, 5, None, {}),
    "E-5002": ("Z-OLM", "Olmazor obyekti №2 (sintetik)", 15.75, "auto", 2, 5, None, {}),
    "E-5003": ("Z-OLM", "Olmazor obyekti №3 (sintetik)", 14.0, "auto", 2, 7, None, {}),
    # Sergeli — barcha yashil, qamrov 100% → zona GREEN
    "E-6001": ("Z-SER", "Sergeli obyekti №1 (sintetik)", 24.5, "auto", 3, 4, None, {}),
    "E-6002": ("Z-SER", "Sergeli obyekti №2 (sintetik)", 28.0, "auto", 3, 4, 4.2, {}),
    # O6 — stansiya sanoat zonasidan uzoq
    "E-6003": ("Z-SER", "Sergeli obyekti №3 (sintetik)", 28.0, "auto", 3, 4, None, {"station_far": True}),
}


def _mk_facilities():
    facs = []
    for eco_id, (zone, name, pm25, method, nsrc, rec, bod, flags) in SPECIALS.items():
        facs.append(dict(eco_id=eco_id, name=name, zone_id=zone, pm25=pm25, method=method,
                         nsources=nsrc, recency=rec, bod=bod, flags=flags))
    # har bir zonaga oddiy obyektlar (jami 36+ obyekt)
    seq = {"Z-YUN": 10, "Z-CHI": 10, "Z-MUL": 10, "Z-YAK": 10, "Z-OLM": 10, "Z-SER": 10}
    used = {}
    for i in range(60):
        z = ZONES[i % len(ZONES)][0]
        used[z] = used.get(z, 0) + 1
        eco = f"E-{z[-3:]}{used[z]:02d}"
        if eco in SPECIALS:
            continue
        # Olmazor: faqat har uchinchisi o'lchovli (qamrovni pasaytirish uchun)
        measured = (z != "Z-OLM") or (used[z] % 3 == 0)
        mu, sd = {"Z-YUN": (30.0, 6.0), "Z-CHI": (27.0, 5.0), "Z-MUL": (23.5, 3.5),
                  "Z-YAK": (23.5, 3.5), "Z-OLM": (22.0, 3.5), "Z-SER": (21.5, 3.5)}[z]
        pm25 = round(max(5.0, min(RNG.gauss(mu, sd), 31.0)), 1)  # ≤31 → R<1, yashil
        method = RNG.choice(["auto", "auto_accredited"])       # ishonchli usul → C yuqori
        nsrc = RNG.choice([2, 2, 3])
        rec = RNG.choice([3, 4, 5, 7])
        facs.append(dict(eco_id=eco, name=f"{[x[1] for x in ZONES if x[0]==z][0]} obyekti (sintetik)",
                         zone_id=z, pm25=pm25 if measured else None, method=method,
                         nsources=nsrc, recency=rec, bod=None, flags={}))
    return facs


def seed(conn) -> dict:
    db.init_schema(conn)
    for n in config.NORMS:
        conn.execute("INSERT OR REPLACE INTO norms VALUES (:indicator,:kind,:value,:unit,:basis,:valid_from,:note)", n)
    for z in ZONES:
        conn.execute("INSERT OR REPLACE INTO zones VALUES (?,?,?,?,?)", z)

    facs = _mk_facilities()
    for f in facs:
        zc = [z for z in ZONES if z[0] == f["zone_id"]][0]
        lat = zc[2] + RNG.uniform(-0.02, 0.02)
        lon = zc[3] + RNG.uniform(-0.02, 0.02)
        conn.execute(
            "INSERT OR REPLACE INTO facilities(eco_id,name,zone_id,lat,lon,sector,"
            "station_far_from_industry,natural_source_flag,seasonal_3y_flag,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f["eco_id"], f["name"], f["zone_id"], lat, lon, "sanoat",
             1 if f["flags"].get("station_far") else 0,
             1 if f["flags"].get("natural_source") else 0,
             1 if f["flags"].get("seasonal_3y") else 0, "2026-01-15"))
        for ind, val, norm in (("pm25", f["pm25"], 35.0), ("bod", f["bod"], 6.0)):
            if val is None:
                continue
            conn.execute(
                "INSERT INTO measurements(eco_id,indicator,value,measured_at,method,n_sources,source_ref) "
                "VALUES (?,?,?,?,?,?,?)",
                (f["eco_id"], ind, val, (NOW - timedelta(days=f["recency"])).strftime("%Y-%m-%d"),
                 f["method"], f["nsources"], f"gis.uznature.uz/stansiya-{f['eco_id'][-4:]}"))
    conn.commit()

    # ---- zona hisobi (rule_version 1.0) ----
    run = conn.execute(
        "INSERT INTO zoning_runs(scope, rule_version, input_hash, started_at, finished_at, stats) "
        "VALUES (?,?,?,?,?,?)",
        ("Toshkent sh. demo", engine.RULE_VERSION, "demo-42", NOW.strftime("%Y-%m-%d %H:%M:%S"),
         NOW.strftime("%Y-%m-%d %H:%M:%S"), "{}"))
    run_id = run.lastrowid

    results, zone_stats = {}, {}
    for f in facs:
        inds = []
        rows = conn.execute("SELECT * FROM measurements WHERE eco_id=?", (f["eco_id"],)).fetchall()
        for m in rows:
            inds.append(Indicator(code=m["indicator"], value=m["value"], norm=35.0 if m["indicator"] == "pm25" else 6.0,
                                  method=m["method"], n_sources=m["n_sources"],
                                  recency_days=(NOW.date() - datetime.strptime(m["measured_at"], "%Y-%m-%d").date()).days))
        res = compute_facility(inds, planned_indicators=2,
                               appeal_confirmed=bool(f["flags"].get("appeal_confirmed")),
                               station_far_from_industry=bool(f["flags"].get("station_far")),
                               natural_source=bool(f["flags"].get("natural_source")),
                               seasonal_3y=bool(f["flags"].get("seasonal_3y")))
        results[f["eco_id"]] = res
        zs = zone_stats.setdefault(f["zone_id"], {"classes": [], "total": 0, "measured": 0})
        zs["total"] += 1
        zs["classes"].append(res)
        if res["R"] is not None:
            zs["measured"] += 1
        conn.execute(
            "INSERT INTO facility_classes(eco_id, indicator, ratio, confidence, zone_class, severity,"
            " rule_version, reasons, computed_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (f["eco_id"], res.get("indicator") or "pm25", res["R"], res["C"], res["zone"], res["severity"], engine.RULE_VERSION,
             json.dumps(res["reasons"], ensure_ascii=False), NOW.strftime("%Y-%m-%d %H:%M:%S")))
        if res["zone"] in ("red", "yellow") or res["pending_review"]:
            db.add_event(conn, "class_change", eco_id=f["eco_id"], zone_id=f["zone_id"],
                         severity=res["severity"], payload={"zone": res["zone"], "R": res["R"], "C": res["C"],
                         "pending_review": res["pending_review"]},
                         created_at=NOW.strftime("%Y-%m-%d %H:%M:%S"))
    # zona ranglari
    zone_color = {}
    for zid, zs in zone_stats.items():
        coverage = zs["measured"] / zs["total"]
        zone_color[zid] = engine.aggregate_zone(zs["classes"], coverage)
    stats = {"zones": zone_color,
             "distribution": {z: sum(1 for r in results.values() if r["zone"] == z) for z in engine.ZONES},
             "pending_review": sum(1 for r in results.values() if r["pending_review"])}
    conn.execute("UPDATE zoning_runs SET stats=? WHERE run_id=?", (json.dumps(stats, ensure_ascii=False), run_id))
    conn.commit()
    return {"run_id": run_id, "results": results, "zone_stats": zone_stats, "zone_color": zone_color,
            "facilities": facs, "stats": stats}


def seed_appeals(conn) -> list[dict]:
    """Demo murojaatlar — 7 holat, SLA, dublikat."""
    from .murojaat.service import AppealService
    svc = AppealService(conn)
    out = []
    d = lambda days: NOW - timedelta(days=days)

    a1 = svc.create(description="Yunusobod 12-mavzeda kechqurun kuchli tutun hidi sezilmoqda, bir haftadan beri davom etadi.",
                    category="air", lat=41.352, lon=69.281, phone="+998901112233", now=d(15))
    out.append(a1["public_code"])
    svc.transition(a1["public_code"], "ko'rib_chiqilmoqda", "system", now=d(13))
    # 14 kun → muddati o'tgan (10 ish kunidan keyin) → due_events "escalate"

    a2 = svc.create(description="Chilonzor 3-mavzeda qurilish changi ko'cha bo'ylab tarqalmoqda.", category="air",
                    lat=41.278, lon=69.208, phone="+998901112244", now=d(8))
    svc.transition(a2["public_code"], "ko'rib_chiqilmoqda", "system", now=d(8))
    svc.transition(a2["public_code"], "tashkilotga_yuborildi", "operator", now=d(7))
    svc.transition(a2["public_code"], "javob_berildi", "operator",
                   comment="Hududiy boshqarma javobi: o'lchov o'tkazildi, natija e'lon qilinadi.", now=d(4))
    out.append(a2["public_code"])

    a3 = svc.create(description="Journalist so'rovi: Sergeli poligoniga olib boriladigan yo'lda chang normadan oshganmi?",
                    category="waste", lat=41.221, lon=69.223, phone="+998901112255", author_kind="journalist", now=d(6))
    out.append(a3["public_code"])   # jurnalist SLA 5 kun → muddati o'tgan

    a4 = svc.create(description="Yakkasaroyda tungi vaqtda yoqimsiz hid tarqalmoqda, manba noma'lum.", category="odor",
                    lat=41.286, lon=69.264, phone="+998901112266", now=d(20))
    svc.transition(a4["public_code"], "ko'rib_chiqilmoqda", "system", now=d(19))
    svc.transition(a4["public_code"], "tashkilotga_yuborildi", "operator", now=d(18))
    svc.transition(a4["public_code"], "javob_berildi", "operator",
                   comment="Hududiy boshqarma Javobi: manba aniqlanmadi.", now=d(17))
    svc.transition(a4["public_code"], "rad_etildi", "operator",
                   comment="Sabab: ko'rsatilgan manzil bo'yicha manba tasdiqlanmadi (meteorologik sharoit).", now=d(12))
    svc.transition(a4["public_code"], "apellyatsiya", "citizen", now=d(5))
    out.append(a4["public_code"])

    a5 = svc.create(description="Olmazor tumanida kanalizatsiya suvi ochiq ariqqa oqizilmoqda (foto ilova qilinadi).",
                    category="water", lat=41.346, lon=69.212, phone="+998901112277", now=d(2))
    out.append(a5["public_code"])

    # Dublikat juftligi (bir xil matn, 100 m, bir xil kun) → birlashtirish
    txt = "Mirzo Ulug'bek tumanida zavod mo'risidan qora tutun chiqmoqda, kechasi ham to'xtamaydi."
    a6 = svc.create(description=txt, category="air", lat=41.326, lon=69.331, phone="+998901112288", now=d(1))
    m = svc.create(description=txt, category="air", lat=41.3265, lon=69.3312, phone="+998901112299", now=d(1) + timedelta(hours=2))
    out.append(a6["public_code"])
    # 0,55–0,85 o'xshashlik → guruh
    a7 = svc.create(description="Mirzo Ulug'bekda zavod mo'ridan qora tutun chiqadi, kechasi ayniqsa kuchli.",
                    category="air", lat=41.3258, lon=69.3305, phone="+998901112300", now=d(1) + timedelta(hours=3))
    out.append(a7["public_code"])

    # hal_qilindi (dalil bilan)
    a8 = svc.create(description="Yunusobodda chang ushlagich ishlamayotgan ko'rinadi, chang ko'tarilmoqda.", category="air",
                    lat=41.354, lon=69.283, phone="+998901112311", now=d(9))
    svc.transition(a8["public_code"], "ko'rib_chiqilmoqda", "system", now=d(9))
    svc.transition(a8["public_code"], "tashkilotga_yuborildi", "operator", now=d(8))
    svc.transition(a8["public_code"], "hal_qilindi", "operator",
                   comment="Uskuna ta'mirlandi.",
                   evidence="o'lchov: 18 µg/m³ (o'lchov dalolatnomasi 2026-11-10)", now=d(3))
    out.append(a8["public_code"])

    return out, {"merged": m, "similar_group": a7.get("similar_group")}
