# -*- coding: utf-8 -*-
"""S7 — to'liq demo: seed → hisob → murojaatlar → hisobot → xarita."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config, db                       # noqa: E402
from src.seed import NOW, ZONES, seed, seed_appeals  # noqa: E402
from src.murojaat.service import AppealService   # noqa: E402
from src.llm.generate import generate            # noqa: E402
from src.zoning import engine                    # noqa: E402

ZONE_UI = {"red": ("#C0392B", "Qizil"), "yellow": ("#F5A623", "Sariq"),
           "green": ("#2E9E5B", "Yashil"), "blue": ("#6E8CA0", "Ko'k-neytral")}


def main():
    db_path = config.DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = db.connect(db_path)
    res = seed(conn)
    codes, dup_info = seed_appeals(conn)

    svc = AppealService(conn)
    sla = svc.sla_report(now=NOW)
    due = svc.due_events(now=NOW)
    conn.execute("INSERT INTO sla_metrics(body, period, median_days, compliance_pct, open_count, overdue_pct, computed_at) "
                 "VALUES (?,?,?,?,?,?,?)",
                 ("barcha organlar", "2026-11", sla["median_response_days"], sla["compliance_pct"],
                  sla["open"], sla["overdue_pct"], NOW.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

    # --- S4: matn generatsiyasi (top-3 qizil/sariq) ---
    classes = {r["eco_id"]: dict(r) for r in conn.execute(
        "SELECT fc.*, f.name, f.zone_id FROM facility_classes fc JOIN facilities f USING(eco_id) "
        "WHERE fc.id IN (SELECT MAX(id) FROM facility_classes GROUP BY eco_id)")}
    top = sorted([c for c in classes.values() if c["ratio"]], key=lambda c: -c["ratio"])[:3]
    texts = []
    for c in top:
        m = conn.execute("SELECT value FROM measurements WHERE eco_id=? AND indicator='pm25'", (c["eco_id"],)).fetchone()
        payload = {"facility": c["name"], "zone": c["zone_class"], "ratio": c["ratio"],
                   "value": m["value"] if m else None, "norm": 35.0, "unit": "µg/m³",
                   "confidence": c["confidence"], "reasons": json.loads(c["reasons"] or "[]")[:2],
                   "source": f"gis.uznature.uz/stansiya-{c['eco_id'][-4:]}", "updated_at": NOW.strftime("%Y-%m-%d")}
        g = generate(payload, "bot")
        conn.execute(
            "INSERT INTO generated_texts(format, model, prompt_version, input_hash, text, verify_status, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (g["format"], g["model"], g["prompt_version"], g["input_hash"], g["text"],
             g["verify_status"], NOW.strftime("%Y-%m-%d %H:%M:%S")))
        texts.append(g)
    conn.commit()

    # --- CSV eksport ---
    os.makedirs(os.path.join(config.BASE_DIR, "data"), exist_ok=True)
    with open(os.path.join(config.BASE_DIR, "data", "measurements.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["eco_id", "zone_id", "indicator", "value", "norm", "method", "n_sources", "source_ref"])
        for r in conn.execute("SELECT * FROM measurements"):
            w.writerow([r["eco_id"], r["zone_id"] if "zone_id" in r.keys() else "",
                        r["indicator"], r["value"], 35.0 if r["indicator"] == "pm25" else 6.0,
                        r["method"], r["n_sources"], r["source_ref"]])

    # --- xarita ---
    os.makedirs(os.path.join(config.BASE_DIR, "web"), exist_ok=True)
    write_map(conn, classes, res)

    # --- hisobot ---
    write_report(conn, res, classes, codes, dup_info, sla, due, texts)
    dist = res["stats"]["distribution"]
    print("Demo tayyor:")
    print("  obyektlar:", len(res["facilities"]), "| zonа ranglari:", res["zone_color"])
    print("  klass taqsimoti:", dist, "| pending (tekshiruv kutilmoqda):", res["stats"]["pending_review"])
    print("  murojaatlar:", len(codes), "| SLA:", sla, "| due:", due)
    print("  matnlar:", [t["verify_status"] for t in texts])
    print("  fayllar: reports/DEMO-NATIJA.md, web/map.html, data/measurements.csv")


def write_map(conn, classes, res):
    geo = {"type": "FeatureCollection", "features": []}
    for z in conn.execute("SELECT * FROM zones"):
        zid = z["zone_id"]
        zs = res["zone_stats"][zid]
        coverage = zs["measured"] / zs["total"]
        color = res["zone_color"][zid]
        d = 0.02
        poly = [[z["center_lon"] - d, z["center_lat"] - d], [z["center_lon"] + d, z["center_lat"] - d],
                [z["center_lon"] + d, z["center_lat"] + d], [z["center_lon"] - d, z["center_lat"] + d]]
        geo["features"].append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [poly]},
                                "properties": {"name": z["name"], "zone_color": color,
                                               "coverage": round(coverage, 2), "measured": zs["measured"],
                                               "total": zs["total"]}})
    facs = []
    for eco_id, c in classes.items():
        f = conn.execute("SELECT * FROM facilities WHERE eco_id=?", (eco_id,)).fetchone()
        facs.append({"eco_id": eco_id, "name": c["name"], "lat": f["lat"], "lon": f["lon"],
                     "zone": c["zone_class"], "R": c["ratio"], "C": c["confidence"],
                     "reasons": json.loads(c["reasons"] or "[]")[:1]})
    legend = "".join(
        f'<div class="lg"><span style="background:{c}"></span>{n}</div>' for c, n in
        [(ZONE_UI["red"][0], "Qizil — R ≥ 2,0"), (ZONE_UI["yellow"][0], "Sariq — 1,0 < R < 2,0"),
         (ZONE_UI["green"][0], "Yashil — R ≤ 1,0 va C ≥ 0,5"),
         (ZONE_UI["blue"][0], "Ko'k-neytral — ma'lumot yo'q/tekshirilmagan (<b>toza degani emas</b>)")])
    html = f"""<!doctype html><html lang="uz"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ochiq-Eko-Ledger — demo xarita</title>
<style>
 body{{font-family:system-ui,sans-serif;margin:0;background:#0f1720;color:#e8eef4}}
 header{{padding:14px 18px;background:#132030;border-bottom:1px solid #22384f}}
 h1{{font-size:17px;margin:0 0 4px}} .sub{{font-size:12px;color:#9fb3c8}}
 #wrap{{display:flex;flex-wrap:wrap;gap:16px;padding:16px}}
 #map{{flex:2 1 520px;min-width:320px}} svg{{width:100%;height:auto;background:#16232f;border-radius:10px}}
 #side{{flex:1 1 300px;min-width:260px}}
 .lg{{font-size:13px;margin:6px 0;display:flex;align-items:center;gap:8px}}
 .lg span{{width:16px;height:16px;border-radius:4px;display:inline-block}}
 table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}}
 td,th{{border-bottom:1px solid #22384f;padding:5px 4px;text-align:left}}
 .R{{font-weight:700}} .pill{{padding:1px 7px;border-radius:9px;font-size:11px;color:#08131c}}
 @media(max-width:768px){{#map{{order:2}}#side{{order:1}}}}
</style>
<header><h1>Ochiq-Eko-Ledger MVP — zona xaritasi (demo)</h1>
<div class="sub">rule_version {engine.RULE_VERSION} · sintetik ma'lumotlar · ko'k zona = ma'lumot yo'q, <b>toza degani emas</b></div></header>
<div id="wrap">
 <div id="map"><svg id="svg" viewBox="0 0 1000 660"></svg></div>
 <div id="side">
  <div>{legend}</div>
  <table id="tbl"><tr><th>Zona</th><th>Rang</th><th>Qamrov</th></tr></table>
 </div>
</div>
<script>
const GEO={json.dumps(geo)}; const FACS={json.dumps(facs)};
const COLORS={{red:'{ZONE_UI["red"][0]}',yellow:'{ZONE_UI["yellow"][0]}',green:'{ZONE_UI["green"][0]}',blue:'{ZONE_UI["blue"][0]}'}};
const NAME={{red:'Qizil',yellow:'Sariq',green:'Yashil',blue:"Ko'k-neytral"}};
const svg=document.getElementById('svg'); const t=document.getElementById('tbl');
const P=(lon,lat)=>[(lon-69.15)*(1000/0.30),(660-(lat-41.16)*(660/0.24))];
function poly(pts){{return pts.map(p=>P(p[0],p[1]).join(',')).join(' ')}}
GEO.features.forEach(f=>{{
 const pts=f.geometry.coordinates[0]; const z=f.properties.zone_color;
 const el=document.createElementNS('http://www.w3.org/2000/svg','polygon');
 el.setAttribute('points',poly(pts)); el.setAttribute('fill',COLORS[z]); el.setAttribute('fill-opacity',0.30);
 el.setAttribute('stroke',COLORS[z]); el.setAttribute('stroke-width','2');
 if(z==='blue') el.setAttribute('stroke-dasharray','6 4');
 el.appendChild(Object.assign(document.createElementNS('http://www.w3.org/2000/svg','title'),{{textContent:f.properties.name+' — '+NAME[z]+' · qamrov '+Math.round(f.properties.coverage*100)+'% ('+f.properties.measured+'/'+f.properties.total+')'}}));
 svg.appendChild(el);
 const c=P(pts[0][0]+0.02,pts[0][1]+0.02);
 const lb=document.createElementNS('http://www.w3.org/2000/svg','text');
 lb.setAttribute('x',c[0]); lb.setAttribute('y',c[1]); lb.setAttribute('fill','#cfe0ef');
 lb.setAttribute('font-size','13'); lb.textContent=f.properties.name; svg.appendChild(lb);
 const row=t.insertRow(); row.innerHTML='<td>'+f.properties.name+'</td><td><span class="pill" style="background:'+COLORS[z]+'">'+NAME[z]+'</span></td><td>'+f.properties.measured+'/'+f.properties.total+' ('+Math.round(f.properties.coverage*100)+'%)</td>';
}});
FACS.forEach(f=>{{ const c=P(f.lon,f.lat);
 const el=document.createElementNS('http://www.w3.org/2000/svg','circle');
 el.setAttribute('cx',c[0]); el.setAttribute('cy',c[1]); el.setAttribute('r',6);
 el.setAttribute('fill',COLORS[f.zone]); el.setAttribute('stroke','#0b1218');
 el.appendChild(Object.assign(document.createElementNS('http://www.w3.org/2000/svg','title'),{{textContent:f.name+' · R='+f.R+' · C='+f.C+' · '+NAME[f.zone]}}));
 svg.appendChild(el);}});
</script></html>"""
    with open(config.WEB_MAP, "w", encoding="utf-8") as fh:
        fh.write(html)


def write_report(conn, res, classes, codes, dup_info, sla, due, texts):
    dist = res["stats"]["distribution"]
    lines = ["# MVP demo natijasi (avtomatik hisobot)", "",
             f"**Sana:** {NOW} · **rule_version:** {engine.RULE_VERSION} · **obyektlar:** {len(res['facilities'])}", ""]
    lines += ["## 1. Zona ranglari (agregatsiya, TZ §5.5)", "",
              "| Zona | Rang | Qamrov | Izoh |", "|---|---|---|---|"]
    for z in ZONES:
        zid = z[0]
        zs = res["zone_stats"][zid]
        cov = f"{zs['measured']}/{zs['total']} ({round(100*zs['measured']/zs['total'])}%)"
        lines.append(f"| {z[1]} | **{res['zone_color'][zid]}** | {cov} | {ZONE_UI[res['zone_color'][zid]][1]} |")
    lines += ["", f"Klass taqsimoti: " + ", ".join(f"{k}={v}" for k, v in dist.items()) +
              f" · «tekshiruv kutilmoqda» (ko'k+shtrix): {res['stats']['pending_review']}", ""]
    lines += ["## 2. Maxsus holatlar (override qoidalari ishlaydi)", ""]
    for eco, c in sorted(classes.items()):
        if c["ratio"] is None or c["zone_class"] == "green":
            continue
        reasons = json.loads(c["reasons"] or "[]")
        ov = ""
        for r in reasons:
            for code in ("O1", "O2", "O3", "O4", "O5", "O6"):
                if r.startswith(code):
                    ov += code + " "
        lines.append(f"- **{c['name']}** ({eco}): R={c['ratio']}, C={c['confidence']}, "
                     f"rang={c['zone_class']}, severity={c['severity']}"
                     + (f", override: {ov.strip()}" if ov else ""))
    lines += ["", "## 3. Murojaat moduli (SLA, TZ §6.5)", "",
              f"- Yaratilgan murojaatlar: **{len(codes)}** ({', '.join(codes)})",
              f"- SLA hisoboti: median javob = {sla['median_response_days']} kun, "
              f"muddatga rioya = {sla['compliance_pct']}%, ochiq = {sla['open']}, muddati o'tgan = {sla['overdue']}",
              f"- 7/10/15-kun hodisalari: {json.dumps(due, ensure_ascii=False)}",
              f"- Dublikat birlashtirish: {json.dumps(dup_info['merged'], ensure_ascii=False) if isinstance(dup_info['merged'], dict) else dup_info['merged']}",
              f"- O'xshash guruh (0,55–0,85): {dup_info.get('similar_group')}", ""]
    lines += ["## 4. Matn generatori (S4 — verifikatsiya)", ""]
    for t in texts:
        lines.append(f"- **{t['format']}** [{t['verify_status']}] · hash `{t['input_hash']}`")
        lines.append(f"  > {t['text']}")
    lines += ["", "## 5. Fayllar", "",
              "- Xarita: `web/map.html` (o'z-o'zini ta'minlaydi, tashqi CDN yo'q)",
              "- API: `uvicorn src.api.app:app` → `/v1/health`, `/v1/geo/zones.geojson`, `/v1/kpi/sla`",
              "- CSV eksport: `data/measurements.csv` (ochiq ma'lumot talabi — Aarhus 4-modda)  ", ""]
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    with open(os.path.join(config.REPORTS_DIR, "DEMO-NATIJA.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    main()
