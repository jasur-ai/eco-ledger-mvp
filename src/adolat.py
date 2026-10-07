# -*- coding: utf-8 -*-
"""Adolat paketi — tushuntirish kartasi va choraklik «Aniqlik hisoboti».

Manba: `01-Loyiha1-Carbon-Emission/Tadqiqotlar/Tadqiqot_1C_Adolat_Paketi.md`
  §C.2 — «tushuntirish kartasi»: 12 majburiy maydon (bir sahifa, o'zbek lotin + rus)
  §D.2 — apellyatsiya oqimi (muddatlar, kanal)
  §E.2 — 5 ochiq metrika (choraklik hisobot), «juftlikda e'lon qilish» qoidasi

Tamoyil: **karta hech narsani yashirmaydi** — ma'lumot bazada yo'q bo'lsa, maydon
«mavjud emas» deb belgilanadi va sabab ko'rsatiladi (bo'sh joy «0» yoki «—» bilan
yashirilmaydi: bu 1C ning asosiy talabi).
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

# L2 kontekstida (fuqaro platformasi) jarima yo'q — 9/10-maydonlar shu sababdan «qo'llanilmaydi»
KARTA_MAJBURIY = 12

# Apellyatsiya muddatlari (§D.1/D.2): javob — 10 kun (platforma standarti),
# apellyatsiya oynasi — 30 ish kuni (O'RQ-457 bilan mos)
JAVOB_KUN = 10
APELLYATSIYA_ISH_KUNI = 30


def _one(conn, sql: str, args: tuple = ()) -> Any:
    row = conn.execute(sql, args).fetchone()
    return row[0] if row else None


def _row(conn, sql: str, args: tuple = ()) -> Any:
    return conn.execute(sql, args).fetchone()


# ------------------------------------------------------------------ 1) tushuntirish kartasi

def explain_card(conn, eco_id: str) -> dict:
    """1C §C.2 — 12 maydonli «tushuntirish kartasi» (bir qaror uchun pasport).

    Har maydon: {"qiymat": …, "manba": …, "holat": "bor" | "mavjud emas" | "qo'llanilmaydi"}
    """
    f = _row(conn, "SELECT eco_id, name, zone_id, lat, lon, sector, "
                   "station_far_from_industry, natural_source_flag, seasonal_3y_flag "
                   "FROM facilities WHERE eco_id=?", (eco_id,))
    if not f:
        raise ValueError(f"Obyekt topilmadi: {eco_id}")

    cls = _row(conn, "SELECT indicator, ratio, confidence, zone_class, severity, rule_version, "
                     "reasons, computed_at FROM facility_classes WHERE eco_id=? "
                     "ORDER BY computed_at DESC, id DESC LIMIT 1", (eco_id,))
    # R58 tuzatishi: o'lchov va norma — klassi hisoblangan AYNAN o'sha indikator bo'yicha
    ind = (cls[0] if cls else None)
    m = _row(conn, "SELECT indicator, value, measured_at, method, n_sources, source_ref "
                   "FROM measurements WHERE eco_id=? AND (? IS NULL OR indicator=?) "
                   "ORDER BY measured_at DESC, id DESC LIMIT 1", (eco_id, ind, ind))
    if m is None:      # klassi bor, o'lchovi yo'q — oxirgi mavjud o'lchovni ko'rsatamiz
        m = _row(conn, "SELECT indicator, value, measured_at, method, n_sources, source_ref "
                       "FROM measurements WHERE eco_id=? ORDER BY measured_at DESC, id DESC LIMIT 1", (eco_id,))
        ind = m[0] if m else ind
    norm = _row(conn, "SELECT value, unit, basis, valid_from FROM norms WHERE indicator=? "
                      "AND kind IN ('one_time', 'discharge') "
                      "ORDER BY CASE kind WHEN 'one_time' THEN 0 ELSE 1 END LIMIT 1",
                (m[0] if m else (ind or ""),))
    last_appeal = _row(conn, "SELECT public_code, status, responsible_body FROM appeals "
                             "WHERE eco_id=? ORDER BY created_at DESC LIMIT 1", (eco_id,)) \
        if _has(conn, "appeals") else None

    kartochka: dict[str, dict] = {
        "1_obyekt_va_manba": {
            "qiymat": f"{f[1]} ({f[0]}) · zonalar: {f[2]} · sektor: {f[5]} · "
                      f"koordinata: {f[3]:.4f}, {f[4]:.4f}",
            "manba": "facilities jadvali; o'lchov manbasi — measurements.source_ref",
            "holat": "bor",
        },
        "2_olchash_oynasi": {
            "qiymat": (f"{m[2]} · usul: {m[3]} · manbalar soni: {m[4]}" if m else None),
            "manba": "measurements.measured_at / method / n_sources",
            "holat": "bor" if m else "mavjud emas",
        },
        "3_qiymat": {
            "qiymat": (f"{m[1]} {norm[1]}" if m and norm else (str(m[1]) if m else None)),
            "manba": "measurements.value; birlik — norms.unit",
            "holat": "bor" if m else "mavjud emas",
        },
        "4_noaniqlik_U": {
            "qiymat": None,
            "manba": "o'lchov noaniqligi (k=2) — kalibrovka/sinov hisobotidan olinadi",
            "holat": "mavjud emas",
            "sabab": "Platformada hozircha U maydoni yo'q: manba hujjatlarda noaniqlik "
                     "ko'rsatilmagan (Tadqiqot 1B: UZ bo'yicha tizimli o'lchanmagan). "
                     "TZ-1 piloti shu maydonni to'ldiradi — keyin karta avtomatik chiqaradi.",
        },
        "5_chegara_L": {
            "qiymat": (f"{norm[0]} {norm[1]} · asos: {norm[2]} · kuchga kirgan: {norm[3]}" if norm else None),
            "manba": "norms jadvali (SanQvaM 0053-23 va h.k.)",
            "holat": "bor" if norm else "mavjud emas",
        },
        "6_qaror_qoidasi": {
            "qiymat": (f"zona: {qoida_matni(cls[3], sabablar_royxati(cls[6]))} · R={cls[1]:.2f} · C={cls[2]:.2f} · "
                       f"severity={cls[4]} · qoida versiyasi {cls[5]}" if cls else None),
            "manba": "TZ §5.1–5.4 (R = qiymat/norma; C — ishonch; override qoidalari)",
            "holat": "bor" if cls else "mavjud emas",
            "sabablar": cls[6] if cls else None,
        },
        "7_kalibrovka_holati": {
            "qiymat": (f"usul: {m[3]}" if m else None),
            "manba": "measurements.method (auto_accredited / self_report)",
            "holat": "qisman",
            "sabab": "Kalibrovka sanasi va natijasi alohida maydon sifatida saqlanmaydi — "
                     "TZ-1 D3 oqimi (uskuna jurnali) shu maydonni beradi.",
        },
        "8_xom_malumot_havolasi": {
            "qiymat": (m[5] if m else None),
            "manba": "measurements.source_ref + /v1/export/measurements.csv (ochiq eksport)",
            "holat": "bor" if m else "mavjud emas",
        },
        "9_koeffitsient": {
            "qiymat": None,
            "manba": "1C §A: 202-son Nizom bo'yicha 1×–20× koeffitsient",
            "holat": "qo'llanilmaydi",
            "sabab": "Bu platforma **jarima hisoblamaydi** (ochiq xabar qatlami). Koeffitsient "
                     "faqat nazorat organi qarorida chiqadi — karta o'sha qaror bilan birga to'ldiriladi.",
        },
        "10_summa_va_muddat": {
            "qiymat": None,
            "manba": "1C §A (hisoblangan summa, to'lash muddati)",
            "holat": "qo'llanilmaydi",
            "sabab": "9-maydon bilan bir xil: platforma moliyaviy qaror chiqarmaydi.",
        },
        "11_inson_tekshiruvi": {
            "qiymat": (_human_review(conn, eco_id)),
            "manba": "audit_log; apellyatsiya bo'lsa — appeals.responsible_body",
            "holat": "bor" if _human_review(conn, eco_id) else "mavjud emas",
        },
        "12_etiroz_yoli": {
            "qiymat": (f"javob muddati — {JAVOB_KUN} kun; apellyatsiya oynasi — {APELLYATSIYA_ISH_KUNI} ish kuni "
                       f"(O'RQ-457); kanal: bot (/murojaat), sayt formasi, ochiq kod bilan; "
                       f"mas'ul: {last_appeal[2] if last_appeal else 'hududiy Ekologiya boshqarmasi'}"),
            "manba": "TZ §6.5 (7 holat, 10 kunlik SLA) + 1C §D.2",
            "holat": "bor",
        },
    }

    return {
        "eco_id": eco_id,
        "sana": date.today().isoformat(),
        "maydonlar_soni": len(kartochka),
        "kartochka": kartochka,
        "tolgan_maydonlar": sum(1 for v in kartochka.values() if v["holat"] == "bor"),
        "uch_savol": {
            "nima_olchandi": (f"{m[2]}: {m[1]} {norm[1] if norm else ''} (usul: {m[3]})" if m else "ma'lumot yo'q"),
            "nega_shunday_qaror": (_nega_matni(m, norm, cls, sabablar_royxati(cls[6]))
                                   if (m and norm and cls) else "hisob uchun ma'lumot yetarli emas"),
            "qanday_etiroz": (f"Botdan /murojaat yoki sayt formasi orqali; javob {JAVOB_KUN} kunda; "
                              f"apellyatsiya — {APELLYATSIYA_ISH_KUNI} ish kuni ichida"),
        },
    }


def _insp_result(evidence: str | None) -> str | None:
    """`evidence` matnidan `natija=<qiymat>` ni ajratadi (8-holat yozuvi)."""
    for part in (evidence or "").split(";"):
        part = part.strip()
        if part.startswith("natija="):
            return part.split("=", 1)[1].strip().lower()
    return None


def _has(conn, table: str) -> bool:
    return _one(conn, "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)) is not None


def _human_review(conn, eco_id: str) -> str | None:
    if not _has(conn, "audit_log"):
        return None
    row = _row(conn, "SELECT actor, ts, action FROM audit_log WHERE entity_id=? "
                     "ORDER BY ts DESC LIMIT 1", (eco_id,))
    if not row:
        return None
    return f"oxirgi harakat: {row[2]} · kim: {row[0]} · {row[1]}"


# ------------------------------------------------------------------ 1b) chop etiladigan karta

HOLAT_BELGI = {"bor": "✅", "qisman": "🟡", "mavjud emas": "⚪", "qo'llanilmaydi": "➖"}


def qr_svg(data: str, scale: int = 2, border: int = 1) -> str | None:
    """QR kod (SVG, tashqi resurs yo'q). `segno` bo'lmasa — None (karta QR'siz chiqadi)."""
    try:
        import segno
    except Exception:
        return None
    q = segno.make(data, error="m")
    return q.svg_inline(scale=scale, border=border, dark="#111", light="#fff")


def card_html(conn, eco_id: str, base_url: str = "https://egaz-audit.pages.dev",
              lang: str = "uz") -> str:
    """Bir varaqli chop etiladigan karta (A4) — 1C §C.2: uz lotin (asosiy) + ruscha e'tiroz matni."""
    card = explain_card(conn, eco_id)
    t = card["uch_savol"]
    url = f"{base_url}/v1/adolat/karta/{eco_id}"
    qr = qr_svg(url)

    rows = []
    for key, v in card["kartochka"].items():
        nomi = key.split("_", 1)[1].replace("_", " ")
        qiymat = v["qiymat"] if v["qiymat"] else ("—" if v["holat"] != "mavjud emas" else "ko'rsatilmagan")
        sabab = f'<div class="sabab">{v["sabab"]}</div>' if v.get("sabab") else ""
        sabablar = ""
        if v.get("sabablar"):
            royxat = sabablar_royxati(v["sabablar"])
            if royxat:
                sabablar = "<ul>" + "".join(f"<li>{x}</li>" for x in royxat) + "</ul>"
        rows.append(
            f'<tr><td class="no">{key.split("_")[0]}</td>'
            f'<td><b>{nomi}</b><div class="q">{qiymat}</div>{sabablar}{sabab}</td>'
            f'<td class="manba">{v["manba"]}</td>'
            f'<td class="holat">{HOLAT_BELGI.get(v["holat"], "")} {v["holat"]}</td></tr>')

    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tushuntirish kartasi — {eco_id}</title>
<style>
  @page {{ size: A4; margin: 12mm; }}
  body {{ font: 12.5px/1.5 -apple-system, "Segoe UI", Roboto, Arial, sans-serif; color: #111; margin: 0; }}
  .wrap {{ max-width: 190mm; margin: 0 auto; padding: 10px 14px 24px; }}
  header {{ border-bottom: 2px solid #111; padding-bottom: 8px; margin-bottom: 12px; }}
  h1 {{ font-size: 17px; margin: 0 0 4px; }}
  .sub {{ font-size: 11.5px; color: #555; }}
  .top {{ display: flex; gap: 14px; align-items: flex-start; }}
  .savol {{ background: #f4f7fa; border-left: 4px solid #2f81f7; padding: 9px 11px; margin: 10px 0 12px; }}
  .savol div {{ margin: 2px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; }}
  td, th {{ border-bottom: 1px solid #ccc; padding: 5px 6px; vertical-align: top; text-align: left; }}
  th {{ background: #f0f0f0; font-size: 11px; text-transform: uppercase; letter-spacing: .03em; }}
  .no {{ width: 22px; text-align: center; font-weight: 700; color: #555; }}
  .manba {{ width: 33%; color: #555; font-size: 10.5px; }}
  .holat {{ width: 96px; font-size: 10.5px; white-space: nowrap; }}
  .q {{ font-weight: 600; }}
  .sabab {{ color: #8a4b00; font-size: 10.5px; margin-top: 3px; }}
  ul {{ margin: 4px 0 0 16px; padding: 0; color: #333; }}
  .qr {{ text-align: center; font-size: 10px; color: #555; }}
  .qr svg {{ width: 96px; height: 96px; }}
  .etiroz {{ border: 1px solid #bbb; border-radius: 8px; padding: 9px 11px; margin-top: 10px;
             white-space: pre-line; font-size: 11px; background: #fafafa; }}
  .imzo {{ margin-top: 14px; display: flex; justify-content: space-between; font-size: 11px; }}
  .imzo div {{ border-top: 1px solid #888; width: 30%; padding-top: 4px; }}
  footer {{ margin-top: 12px; font-size: 10px; color: #666; border-top: 1px solid #ddd; padding-top: 6px; }}
  @media print {{ .wrap {{ padding: 0 }} }}
</style></head><body><div class="wrap">
<header>
  <div class="top">
    <div style="flex:1">
      <h1>Tushuntirish kartasi — bitta qarorning pasporti</h1>
      <div class="sub">Obyekt: <b>{eco_id}</b> · sana: {card['sana']} · manba: Ochiq-Eko-Ledger ochiq reyestri ·
        karta 12 majburiy maydondan iborat (1C §C.2)</div>
    </div>
    <div class="qr">{qr or ''}<div>QR: xom ma'lumot va API</div></div>
  </div>
</header>

<div class="savol">
  <div><b>1) Nima o'lchandi:</b> {t['nima_olchandi']}</div>
  <div><b>2) Nega shunday qaror chiqdi:</b> {t['nega_shunday_qaror']}</div>
  <div><b>3) Qanday e'tiroz bildiraman:</b> {t['qanday_etiroz']}</div>
</div>

<table>
  <thead><tr><th></th><th>Maydon</th><th>Manba</th><th>Holat</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>

<div class="etiroz">{objection_text(card, 'uz')}

{objection_text(card, 'ru')}</div>

<div class="imzo">
  <div>Obyekt / korxona vakili</div>
  <div>Tekshiruvchi (kim, qachon)</div>
  <div>Sana, imzo</div>
</div>

<footer>
  Karta avtomatik yaratildi: <code>{url}</code> · to'lgan maydonlar: {card['tolgan_maydonlar']}/12 ·
  yetmaganlari sababi bilan ko'rsatilgan (yashirilmaydi) · yozuvlar o'chirilmaydi (append-only):
  xato tasdiqlansa — tuzatish qo'shiladi.
</footer>
</div></body></html>"""


# ------------------------------------------------------------------ qaror qoidasi matni

ZONA_ASOSIY = {"red": "Qizil (R ≥ 2,0)", "yellow": "Sariq (1,0 < R < 2,0)",
               "green": "Yashil (R ≤ 1,0, C ≥ 0,5)", "blue": "Ko'k-neytral (ma'lumot yetarli emas)"}


def sabablar_royxati(x) -> list[str]:
    """DB'dagi `reasons` maydoni (JSON matn yoki ro'yxat) → matnlar ro'yxati.

    Ilgari bu qiymat satr sifatida aylanib, HTML'da <li> ichida harfma-harf
    chiqib qolardi (R58 tuzatishi).
    """
    if not x:
        return []
    if isinstance(x, (list, tuple)):
        return [str(i) for i in x]
    try:
        d = json.loads(x)
    except Exception:
        return [str(x)]
    return [str(i) for i in d] if isinstance(d, list) else [str(d)]


def _nega_matni(m, norm, cls, sabablar: list[str]) -> str:
    """«Nega shunday qaror» matni — ko'rsatilgan kasr AYNAN hisoblangan nisbatga mos bo'lishi shart.

    R58 tuzatishi: ilgari o'lchov va norma turli indikatordan olinib, karta ichida
    ziddiyatli arifmetika chiqarardi (masalan «8.4/35.0 = 1.40»). Endi mos kelmasa,
    kasr ko'rsatilmaydi va hisob indikatori ochiq yoziladi.
    """
    qoida = qoida_matni(cls[3], sabablar)
    if not (m and norm):
        return f"R = {cls[1]:.2f} → {qoida}"
    hisob = m[1] / norm[0] if norm[0] else None
    if hisob is not None and abs(hisob - cls[1]) <= max(0.02, abs(cls[1]) * 0.02):
        return f"R = {m[1]}/{norm[0]} = {cls[1]:.2f} → {qoida}"
    return (f"R = {cls[1]:.2f} ({m[0]}-indikatori bo'yicha) → {qoida}"
            f" · ko'rsatilgan o'lchov ({m[1]}) klassi hisoblangan indikatorga mos kelmaydi — qayta hisoblash talab qilinadi")


def qoida_matni(zone: str, sabablar: list[str]) -> str:
    """Zona nomi + ASLIDA qo'llanilgan qoida.

    Muammo (R58 tuzatishi): «Qizil (R ≥ 2,0)» yozuvi override (O1/O2/O3) bilan
    ko'tarilgan holatlarda ham chiqarilar edi — R=1,40 bo'lsa bu ziddiyat.
    Endi override qo'llanilgan bo'lsa, aynan o'sha qoida ko'rsatiladi.
    """
    asosiy = ZONA_ASOSIY.get(zone, zone)
    override = None
    for sabab in sabablar:
        m = re.match(r"^\s*(O\d)\s*:", str(sabab))
        if m and "pog'ona" in str(sabab):
            override = str(sabab).strip()
            break
    if override:
        return f"{asosiy.split(' (')[0]} (qo'llanilgan qoida: {override})"
    return asosiy


# ------------------------------------------------------------------ 2) apellyatsiya matni

def objection_text(card: dict, lang: str = "uz") -> str:
    """12-maydonning «tayyor shablon matni» qismi (fuqaro e'tirozi uchun).

    Uch savolga javob birinchi xatboshida: nima o'lchandi · nega shunday qaror · qanday e'tiroz.
    """
    t = card.get("uch_savol", {})
    if lang == "ru":
        return (
            "ОБЖАЛОВАНИЕ (шаблон)\n"
            f"Объект: {card['eco_id']}\n"
            f"1) Что измерено: {t.get('nima_olchandi')}\n"
            f"2) Почему такое решение: {t.get('nega_shunday_qaror')}\n"
            f"3) Как обжаловать: {t.get('qanday_etiroz')}\n"
            "Прошу: (а) предоставить сырые данные и неопределённость измерения (U, k=2); "
            "(б) провести повторную проверку; (в) при подтверждении ошибки — скорректировать запись "
            "в реестре (запись не удаляется, добавляется исправление)."
        )
    return (
        "E'TIROZ (shablon)\n"
        f"Obyekt: {card['eco_id']}\n"
        f"1) Nima o'lchandi: {t.get('nima_olchandi')}\n"
        f"2) Nega shunday qaror: {t.get('nega_shunday_qaror')}\n"
        f"3) Qanday e'tiroz bildiraman: {t.get('qanday_etiroz')}\n"
        "So'rov: (a) xom ma'lumot va o'lchov noaniqligi (U, k=2) berilsin; (b) qayta tekshiruv "
        "o'tkazilsin; (c) xato tasdiqlansa — registr yozuvi tuzatilsin (yozuv o'chirilmaydi, "
        "tuzatish qo'shiladi — append-only)."
    )


# ------------------------------------------------------------------ 3) choraklik aniqlik hisoboti

def accuracy_report(conn, quarter: str | None = None) -> dict:
    """1C §E.2 — 5 ochiq metrika. Hisoblanmaydiganlari `None` + sabab (yashirilmaydi).

    `quarter` — «2026Q3» ko'rinishida; berilmasa barcha mavjud ma'lumot.
    """
    classes = conn.execute(
        "SELECT fc.eco_id, fc.zone_class, fc.confidence FROM facility_classes fc "
        "JOIN (SELECT eco_id, MAX(id) mid FROM facility_classes GROUP BY eco_id) t ON fc.id = t.mid"
    ).fetchall()
    red = [c for c in classes if c[1] == "red"]
    yellow = [c for c in classes if c[1] == "yellow"]
    signals = len(red) + len(yellow)

    m1 = {"nomi": "Signallar soni", "qiymat": signals, "manba": "facility_classes (red + yellow)",
          "holat": "bor"}

    m2 = {"nomi": "Sariq zona ulushi", "holat": "bor",
          "qiymat": (round(len(yellow) / signals, 4) if signals else None),
          "manba": "sariq / (qizil + sariq) — o'lchov noaniqligining pul oqimiga ta'siri"}

    # 3-metrika: inspeksiya yakunlari (R41 — 8-holat `yakunlandi_tekshiruv`).
    # Manba: appeal_events.evidence ichidagi `natija=tasdiqlandi|qisman|tasdiqlanmadi`.
    insp = {"tasdiqlandi": 0, "qisman": 0, "tasdiqlanmadi": 0}
    if _has(conn, "appeal_events"):
        for (ev,) in conn.execute("SELECT evidence FROM appeal_events WHERE to_status='yakunlandi_tekshiruv'"):
            nat = _insp_result(ev)
            if nat in insp:
                insp[nat] += 1
    n_insp = sum(insp.values())
    if n_insp:
        # precision: tasdiqlangan / (tasdiqlangan + tasdiqlanmagan) — qisman sanalmaydi, ochiq ko'rsatiladi
        denom = insp["tasdiqlandi"] + insp["tasdiqlanmadi"]
        m3 = {"nomi": "Tasdiqlangan qizil signallar (precision)", "holat": "bor",
              "qiymat": (round(insp["tasdiqlandi"] / denom, 4) if denom else None),
              "manba": f"appeal_events (8-holat): tasdiqlandi {insp['tasdiqlandi']} · qisman {insp['qisman']} · "
                       f"tasdiqlanmadi {insp['tasdiqlanmadi']}",
              "izoh": "Qisman tasdiqlangan holatlar maxrajga kirmaydi (ochiq alohida ko'rsatiladi). "
                      "Oyna kichik bo'lsa, foiz barqaror emas — n bilan birga o'qilsin."}
    else:
        m3 = {"nomi": "Tasdiqlangan qizil signallar (precision)", "qiymat": None, "holat": "mavjud emas",
              "manba": "inspeksiya yakunlari kerak (8-holat: `yakunlandi_tekshiruv`)",
              "sabab": "Hozircha inspeksiya yakuni kiritilmagan. Modal tayyor: apellyatsiya/tekshiruv "
                       "jarayonida `yakunlandi_tekshiruv` holatiga o'tish bilan `natija=` yoziladi — "
                       "shundan keyin bu ko'rsatkich avtomatik hisoblanadi (1C §E.2: 1 va 3 juftlikda)."}

    # 4-metric: apellyatsiya ta'siri (qaror o'zgargan holatlar)
    changed = 0
    total_appeals = 0
    if _has(conn, "appeals"):
        total_appeals = _one(conn, "SELECT COUNT(*) FROM appeals") or 0
        changed = _one(conn, "SELECT COUNT(DISTINCT appeal_id) FROM appeal_events "
                             "WHERE from_status IN ('rad_etildi','javob_berildi') "
                             "AND to_status IN ('ko''rib_chiqilmoqda','hal_qilindi')") or 0
    m4 = {"nomi": "Bekor qilingan/o'zgartirilgan qarorlar", "holat": "bor" if total_appeals else "ma'lumot yo'q",
          "qiymat": (round(changed / total_appeals, 4) if total_appeals else None),
          "manba": f"appeal_events: o'zgargan {changed} / jami murojaat {total_appeals}",
          "izoh": "Past qiymat — apellyatsiya ishlamayapti degani EMAS: oyna hali kichik."}

    m5 = {"nomi": "O'rtacha noaniqlik ulushi (U/L)", "qiymat": None, "holat": "mavjud emas",
          "manba": "qurilma kalibrovka hisobotlari (U) va normativ (L)",
          "sabab": "U maydoni platformada hali yo'q (TZ-1 piloti beradi). Ulanishi bilan "
                   "eng zaif bo'g'in (oqim o'lchagichi) ko'rinadigan bo'ladi."}

    return {
        "chorak": quarter or "barcha ma'lumot",
        "sana": date.today().isoformat(),
        "metrikalar": [m1, m2, m3, m4, m5],
        "oskorlik_qoidasi": "1 va 3 ko'rsatkich JUFTLIKDA e'lon qilinadi (1C §E.1: bazaviy daraja "
                            "aytilmasa, foiz chalg'itadi). Hisoblanmaydigan ko'rsatkich «mavjud emas» "
                            "deb yoziladi — nol bilan yashirilmaydi.",
        "qayta_korish_sharti": "3-ko'rsatkich 6 oy ketma-ket pasaysa — tegishli zona chegarasi qayta ko'riladi.",
    }


# ------------------------------------------------------------------ 4) apellyatsiya muddati

def appeal_window(decision_date: str) -> dict:
    """Qaror sanasidan apellyatsiya oynasi (30 ish kuni) va javob muddati (10 kun)."""
    d = datetime.fromisoformat(decision_date).date()
    workdays = 0
    cur = d
    while workdays < APELLYATSIYA_ISH_KUNI:
        cur += timedelta(days=1)
        if cur.weekday() < 5:                       # shanba/yakshanba ish kuni emas
            workdays += 1
    return {
        "qaror_sanasi": d.isoformat(),
        "javob_muddati": (d + timedelta(days=JAVOB_KUN)).isoformat(),
        "apellyatsiya_oxiri": cur.isoformat(),
        "izoh": f"{APELLYATSIYA_ISH_KUNI} ish kuni (dam olish kunlari hisobga olinmagan); "
                f"rasmiy bayramlar qo'shimcha tekshiriladi (O'RQ-457).",
    }
