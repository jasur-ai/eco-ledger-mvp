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
    m = _row(conn, "SELECT indicator, value, measured_at, method, n_sources, source_ref "
                   "FROM measurements WHERE eco_id=? ORDER BY measured_at DESC, id DESC LIMIT 1", (eco_id,))
    norm = _row(conn, "SELECT value, unit, basis, valid_from FROM norms WHERE indicator=? "
                      "AND kind='one_time' LIMIT 1", (cls[0] if cls else (m[0] if m else ""),))
    last_appeal = _row(conn, "SELECT public_code, status, responsible_body FROM appeals "
                             "WHERE eco_id=? ORDER BY created_at DESC LIMIT 1", (eco_id,)) \
        if _has(conn, "appeals") else None

    zone_names = {"red": "Qizil (R ≥ 2,0)", "yellow": "Sariq (1,0 < R < 2,0)",
                  "green": "Yashil (R ≤ 1,0, C ≥ 0,5)", "blue": "Ko'k-neytral (ma'lumot yetarli emas)"}

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
            "qiymat": (f"zona: {zone_names.get(cls[3], cls[3])} · R={cls[1]:.2f} · C={cls[2]:.2f} · "
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
            "nega_shunday_qaror": (f"R = {m[1]}/{norm[0] if norm else '?'} = {cls[1]:.2f} → {zone_names.get(cls[3], cls[3])}"
                                   if (m and norm and cls) else "hisob uchun ma'lumot yetarli emas"),
            "qanday_etiroz": (f"Botdan /murojaat yoki sayt formasi orqali; javob {JAVOB_KUN} kunda; "
                              f"apellyatsiya — {APELLYATSIYA_ISH_KUNI} ish kuni ichida"),
        },
    }


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

    m3 = {"nomi": "Tasdiqlangan qizil signallar (precision)", "qiymat": None, "holat": "mavjud emas",
          "manba": "inspeksiya natijalari (qarorni tasdiqlash) kerak",
          "sabab": "Platformada inspeksiya yakuni maydoni yo'q — bu ko'rsatkich nazorat organi "
                   "ma'lumoti ulanganda hisoblanadi (1C §E.2 qoidasi: 1 va 3 juftlikda e'lon qilinadi)."}

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
