#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tushuntirish kartasini chop etiladigan ko'rinishda chiqarish (HTML va PDF).

Ishlatish:
  python3 scripts/build_card.py --eco E-1001                     # HTML + PDF → reports/kartalar/
  python3 scripts/build_card.py --eco E-1001 --format html
  python3 scripts/build_card.py --eco E-1001 --format pdf --out /tmp/karta.pdf
  python3 scripts/build_card.py --all                            # birinchi 5 qizil zonadagi obyekt

PDF `fpdf2` bilan (o'rnatilmagan bo'lsa — faqat HTML chiqadi va shu haqda ogohlantiradi).
QR kod — `segno` (SVG/PNG ichida, tashqi resurs yo'q).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import adolat, config, db  # noqa: E402

OUTDIR_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "kartalar")


def qr_png_bytes(data: str, scale: int = 4) -> bytes | None:
    try:
        import io

        import segno
    except Exception:
        return None
    buf = io.BytesIO()
    segno.make(data, error="m").save(buf, kind="png", scale=scale, border=1)
    return buf.getvalue()


# PDF da emoji gliflari yo'q (DejaVu) — matnli belgilar (HTML'da esa rangli emoji qoladi)
HOLAT_BELGI_PDF = {"bor": "[OK]", "qisman": "[~]", "mavjud emas": "[-]", "qo'llanilmaydi": "[n/a]"}

DEJAVU = {
    "": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "B": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}


def _register_fonts(pdf) -> tuple[str, str]:
    """DejaVu bo'lsa — to'liq Unicode (o'zbek, rus); bo'lmasa — Helvetica (matn tozalanadi)."""
    if all(os.path.exists(p) for p in DEJAVU.values()):
        for style, path in DEJAVU.items():
            pdf.add_font("DejaVu", style, path)
        return "DejaVu", "DejaVu"
    return "helvetica", "helvetica"


def _t(x, font: str) -> str:
    """Helvetica rejimida latin-1 dan tashqari belgilarni almashtiradi (PDF buzilmasligi uchun)."""
    if font != "helvetica":
        return str(x)
    s = str(x)
    for a_, b_ in (("—", "-"), ("–", "-"), ("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("·", "-")):
        s = s.replace(a_, b_)
    return s.encode("latin-1", "replace").decode("latin-1")


def _short(text, n: int) -> str:
    """PDF uchun qisqartiradi (to'liq matn HTML/API ko'rinishida qoladi)."""
    t = str(text or "").replace("\n", " ").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " …"


def build_pdf(conn, eco_id: str, out_path: str, base_url: str) -> bool:
    """Bir varaqli (A4) karta — 1C §C.2 talabi. To'liq matn: HTML/API (QR havola)."""
    try:
        from fpdf import FPDF
    except Exception:
        return False

    card = adolat.explain_card(conn, eco_id)
    t = card["uch_savol"]
    url = f"{base_url}/v1/adolat/karta/{eco_id}"

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_margins(12, 10, 12)
    FONT, BOLD = _register_fonts(pdf)

    # --- sarlavha + QR
    if qr := qr_png_bytes(url, scale=4):
        import io
        pdf.image(io.BytesIO(qr), x=180, y=10, w=16)
    pdf.set_font(BOLD, "B", 11)
    pdf.cell(0, 5.4, _t("TUSHUNTIRISH KARTASI — bitta qarorning pasporti", FONT), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 7.2)
    pdf.cell(0, 3.6, _t(f"Obyekt: {eco_id} · sana: {card['sana']} · 1C §C.2 — 12 majburiy maydon · "
                        f"to'lgan: {card['tolgan_maydonlar']}/12", FONT), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.4)

    # --- uch savol (1C talabi: birinchi varaqda javob)
    pdf.set_fill_color(244, 247, 250)
    for i2, (k, v) in enumerate(t.items(), 1):
        pdf.set_font(BOLD, "B", 7.4)
        pdf.multi_cell(0, 3.4, _t(f"{i2}) {k.replace('_', ' ')}: {_short(v, 200)}", FONT),
                       fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.2)

    # --- 12 maydon (qisqartirilgan; to'liq matn — HTML/API)
    widths = (6.0, 108.0, 32.0, 42.0)
    pdf.set_font(BOLD, "B", 6.8)
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(widths[0], 3.6, "#", border="B", fill=True)
    pdf.cell(widths[1], 3.6, "Maydon (qisqartirilgan)", border="B", fill=True)
    pdf.cell(widths[2], 3.6, "Holat", border="B", fill=True)
    pdf.cell(widths[3], 3.6, "Manba", border="B", fill=True, new_x="LMARGIN", new_y="NEXT")

    for key, v in card["kartochka"].items():
        nomi = key.split("_", 1)[1].replace("_", " ")
        qiymat = _short(v["qiymat"], 105) if v["qiymat"] else "—"
        sabab = f"  [{_short(v['sabab'], 95)}]" if v.get("sabab") else ""
        pdf.set_font(BOLD, "B", 6.6)
        pdf.cell(widths[0], 3.2, key.split("_")[0], border="B")
        pdf.set_font(FONT, "", 6.5)
        pdf.multi_cell(widths[1], 3.2, _t(f"{nomi}: {qiymat}{sabab}", FONT), border="B", new_x="RIGHT")
        pdf.set_font(FONT, "", 6.1)
        pdf.cell(widths[2], 3.2, _t(HOLAT_BELGI_PDF.get(v["holat"], "") + " " + v["holat"], FONT), border="B")
        pdf.set_font(FONT, "", 5.6)
        pdf.multi_cell(widths[3], 3.2, _t(_short(v["manba"], 58), FONT), border="B", new_x="LMARGIN", new_y="NEXT")

    # --- e'tiroz matni (uz to'liq, ru qisqa) + qolgani havolada
    pdf.ln(1.4)
    pdf.set_font(FONT, "", 6.4)
    pdf.multi_cell(0, 3.0, _t(adolat.objection_text(card, "uz"), FONT), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.8)
    pdf.set_font(FONT, "", 5.8)
    pdf.multi_cell(0, 2.7, _t(_short(adolat.objection_text(card, "ru"), 520), FONT), new_x="LMARGIN", new_y="NEXT")

    # --- imzo va izoh
    pdf.ln(3)
    pdf.set_font(FONT, "", 6.6)
    y = pdf.get_y()
    for i3, lab in enumerate(("Obyekt / korxona vakili", "Tekshiruvchi (kim, qachon)", "Sana, imzo")):
        x = 12 + i3 * 62
        pdf.line(x, y, x + 52, y)
        pdf.set_xy(x, y + 1)
        pdf.cell(52, 3.4, lab)
    pdf.ln(6)
    pdf.set_font(FONT, "", 5.6)
    pdf.multi_cell(0, 2.8, _t(f"To'liq (qisqartirilmagan) karta va xom ma'lumot: {url} · yozuvlar o'chirilmaydi "
                              f"(append-only): xato tasdiqlansa — tuzatish qo'shiladi.", FONT))

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    pdf.output(out_path)
    return True


def build(conn, eco_id: str, fmt: str, out: str | None, base_url: str) -> dict:
    res = {"eco_id": eco_id, "yozildi": []}
    if fmt in ("html", "both"):
        p = out or os.path.join(OUTDIR_DEFAULT, f"karta_{eco_id}.html")
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        open(p, "w", encoding="utf-8").write(adolat.card_html(conn, eco_id, base_url=base_url))
        res["yozildi"].append(p)
    if fmt in ("pdf", "both"):
        p = (out if out and out.endswith(".pdf") else None) or os.path.join(OUTDIR_DEFAULT, f"karta_{eco_id}.pdf")
        ok = build_pdf(conn, eco_id, p, base_url)
        if ok:
            res["yozildi"].append(p)
        else:
            res["ogohlantirish"] = "fpdf2 o'rnatilmagan — PDF chiqarilmadi (HTML ishlaydi)"
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="Tushuntirish kartasi (HTML/PDF)")
    ap.add_argument("--eco", help="obyekt kodi (masalan E-1001)")
    ap.add_argument("--all", action="store_true", help="birinchi 5 qizil zonadagi obyekt")
    ap.add_argument("--format", choices=["html", "pdf", "both"], default="both")
    ap.add_argument("--out", help="aniq fayl yo'li (bitta obyekt uchun)")
    ap.add_argument("--base-url", default=os.environ.get("ECO_BASE_URL", "https://egaz-audit.pages.dev"))
    args = ap.parse_args()

    conn = db.connect()
    targets: list[str] = []
    if args.all:
        rows = conn.execute("SELECT DISTINCT eco_id FROM facility_classes WHERE zone_class='red' LIMIT 5").fetchall()
        targets = [r[0] for r in rows]
    elif args.eco:
        targets = [args.eco]
    else:
        print("--eco yoki --all kerak (--help)")
        return 1

    rc = 0
    for eco in targets:
        try:
            res = build(conn, eco, args.format, args.out if len(targets) == 1 else None, args.base_url)
        except ValueError as e:
            print(f"❌ {eco}: {e}")
            rc = 1
            continue
        print(f"✅ {eco}: " + " · ".join(res["yozildi"]) + (f" ⚠ {res['ogohlantirish']}" if res.get("ogohlantirish") else ""))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
