# -*- coding: utf-8 -*-
"""S4 — matn generatori va 6 qavat verifikatsiya testlari."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.llm.generate import generate, render, verify  # noqa: E402

PAYLOAD = {
    "facility": "Sintetik obyekt-1",
    "zone": "red",
    "ratio": 2.4,
    "value": 84.0,
    "norm": 35.0,
    "unit": "µg/m³",
    "confidence": 0.66,
    "reasons": ["Normadan 2 baravar va undan ko'p oshgan: R=2.40"],
    "source": "gis.uznature.uz/stansiya-1204",
    "updated_at": "2026-11-12",
}


@pytest.mark.parametrize("fmt", ["bot", "press", "weekly"])
def test_generate_pass(fmt):
    g = generate(PAYLOAD, fmt)
    assert g["verify_status"] == "PASS"
    assert all(g["layers"].values())
    assert g["prompt_version"] == "v1" and g["input_hash"]


def test_bot_length_limit():
    g = generate(PAYLOAD, "bot")
    assert len(g["text"]) <= 500


def test_hallucinated_number_fails_v1():
    text = "Obyekt holati red, o'lchov 84 µg/m³, norma 35 — lekin 99 foiz ishonch."
    v = verify(text, PAYLOAD, "bot")
    assert v["status"].startswith("FAIL") and "V1" in v["status"]


def test_banned_words_fail_v3():
    bad = dict(PAYLOAD, reasons=["Tavsiya: zavodni yopish kerak"])
    v = verify(render(bad, "bot"), bad, "bot")
    assert "V3" in v["status"]


def test_missing_source_fails_v4():
    bad = dict(PAYLOAD, source="")
    v = verify(render(bad, "bot"), bad, "bot")
    assert "V4" in v["status"]


def test_blue_zone_never_called_clean():
    p = dict(PAYLOAD, zone="blue", reasons=["Ma'lumot yo'q"])
    t = render(p, "press")
    assert "toza" in t and "degani emas" in t


def test_render_formats_differ():
    assert render(PAYLOAD, "bot") != render(PAYLOAD, "press")
    assert render(PAYLOAD, "weekly").startswith("Haftalik xulosa")


def test_invalid_format_raises():
    with pytest.raises(ValueError):
        render(PAYLOAD, "sms")
