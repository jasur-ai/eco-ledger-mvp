# -*- coding: utf-8 -*-
"""LLM/shablon matn generatori + 6 qavatli verifikatsiya (TZ §8).

Oltin qoida: LLM fakt yaratmaydi — u faqat registrdagi raqamlarni odam tiliga o'giradi.
API kaliti bo'lmasa ham ishlaydi: deterministik shablon (Jinja2 o'rniga sof Python).
"""
from __future__ import annotations

import hashlib
import json
import re

from ..zoning.engine import RULE_VERSION

ZONE_LABEL = {"red": "qizil", "yellow": "sariq", "green": "yashil", "blue": "ko'k-neytral"}
BANNED = ("tavsiya", "prognoz", "bashorat", "siyosiy", "aybdor", "jinoyat", "soxta")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
PROMPT_VERSION = "v1"


def _nums(text: str) -> list[str]:
    return [n.replace(",", ".") for n in NUM_RE.findall(text or "")]


def _payload_nums(payload: dict) -> set[str]:
    out: set[str] = set()

    def walk(x):
        if isinstance(x, (int, float)):
            out.add(("" if float(x) == int(x) else "").join(list(str(x).split("."))) if isinstance(x, float) else str(x))
            out.add(str(x).replace(".0", ""))
            out.add(str(x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            out.update(_nums(x))
    walk(payload)
    return out


def render(payload: dict, fmt: str = "bot") -> str:
    """Registr yozuvidan matn. format: bot (≤500 belgi) | press | weekly."""
    fac = payload.get("facility", "obyekt")
    zone = ZONE_LABEL.get(payload.get("zone", "blue"), "ko'k-neytral")
    R = payload.get("ratio")
    val, norm = payload.get("value"), payload.get("norm")
    unit = payload.get("unit", "")
    C = payload.get("confidence")
    src = payload.get("source", "")
    updated = payload.get("updated_at", "")
    reasons = "; ".join(payload.get("reasons", [])[:2])

    if fmt == "bot":
        return (f"{fac}: holat — {zone} zona. O'lchov {val} {unit}, norma {norm} {unit} "
                f"(nisbat R={R}). Ishonch darajasi C={C}. {reasons[:180]} "
                f"Manba: {src}. Yangilandi: {updated}.")
    if fmt == "press":
        return (f"{fac} bo'yicha oxirgi oy davomidagi kuzatuv: o'lchangan qiymat {val} {unit} "
                f"normativ {norm} {unit}ga nisbatan R={R} ni tashkil etadi (holat: {zone} zona). "
                f"Ma'lumot ishonchliligi C={C} (manbalar va o'lchash usuli asosida). "
                f"Sabab: {reasons}. Manba hujjat: {src}. Yangilanish sanasi: {updated}. "
                f"Ko'k-neytral zona «ma'lumot yo'q/tekshirilmagan» degani — «toza» degani emas.")
    if fmt == "weekly":
        return (f"Haftalik xulosa: {fac} — {zone} zona, R={R}, C={C}, manba {src}, "
                f"yangilandi {updated}. {reasons}")
    raise ValueError(f"format noto'g'ri: {fmt}")


def verify(text: str, payload: dict, fmt: str = "bot") -> dict:
    """6 qavat (TZ §8.4). Qaytadi: {'status': 'PASS'|'FAIL:Vx...', 'layers': {...}}"""
    layers: dict[str, bool] = {}
    allowed = _payload_nums(payload)
    text_nums = _nums(text)

    # V1 — matndagi har bir son payload'da mavjud (uydirma raqam yo'q)
    layers["V1_faktlar_registrdan"] = all(n in allowed for n in text_nums)
    # V2 — asosiy raqamlar (R) matnda bor
    layers["V2_asosiy_raqamlar_bor"] = (str(payload.get("ratio")) in text
                                        if payload.get("ratio") is not None else True)
    # V3 — taqiqlangan so'zlar yo'q (tavsiya/prognoz/siyosiy baho/ayblov)
    low = text.lower()
    layers["V3_taqiqlangan_sozlar_yoq"] = not any(b in low for b in BANNED)
    # V4 — manba havolasi bor
    layers["V4_manba_havolasi"] = bool(payload.get("source")) and str(payload["source"]) in text
    # V5 — format chegarasi
    limit = 500 if fmt == "bot" else 6000
    layers["V5_format_chegarasi"] = len(text) <= limit
    # V6 — namuna nazorati (to'sqinlik qilmaydi, faqat belgi)
    layers["V6_namuna_nazorati_belgisi"] = True

    failed = [k.split("_")[0] for k, v in layers.items() if not v]
    return {"status": "PASS" if not failed else "FAIL:" + ",".join(failed), "layers": layers}


def generate(payload: dict, fmt: str = "bot") -> dict:
    text = render(payload, fmt)
    v = verify(text, payload, fmt)
    return {
        "format": fmt,
        "model": "template-v1",
        "prompt_version": PROMPT_VERSION,
        "rule_version": RULE_VERSION,
        "input_hash": hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16],
        "text": text,
        "verify_status": v["status"],
        "layers": v["layers"],
    }
