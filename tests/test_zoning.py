# -*- coding: utf-8 -*-
"""S2 — zona dvigateli testlari (chegara qiymatlar ±0,01)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.zoning.engine import (Indicator, aggregate_zone, base_zone,  # noqa: E402
                               compute_facility, f_completeness, f_method,
                               f_recency, f_redundancy, severity_of)


# ---------- chegaralar: R × C (TZ §5.1) ----------
@pytest.mark.parametrize("R,C,expected", [
    (0.50, 0.50, "green"), (0.99, 0.50, "green"), (1.00, 0.50, "green"),
    (1.01, 0.50, "yellow"), (1.50, 0.70, "yellow"), (1.99, 0.50, "yellow"),
    (2.00, 0.50, "red"), (2.01, 0.50, "red"), (3.50, 0.80, "red"),
    (5.00, 0.90, "red"), (5.01, 0.90, "red"), (10.00, 1.00, "red"),
    # C chegarasi: 0,5 dan pastda hamma narsa ko'k
    (0.50, 0.49, "blue"), (1.50, 0.49, "blue"), (2.50, 0.49, "blue"),
    (5.00, 0.49, "blue"), (10.00, 0.30, "blue"),
    # C = 0,5 — ishonchli hisoblanadi
    (0.99, 0.50, "green"), (1.01, 0.50, "yellow"), (2.00, 0.50, "red"),
])
def test_base_zone_boundaries(R, C, expected):
    assert base_zone(R, C) == expected


@pytest.mark.parametrize("value,method,nsrc,rec,expected_zone,pending", [
    (84.0, "self_report", 1, 40, "blue", True),    # R=2,4 + C=0,473 → ko'k + «tekshiruv kutilmoqda»
    (84.0, "auto_accredited", 3, 3, "red", False),  # R=2,4 + C=1,0 → qizil
    (28.0, "self_report", 1, 40, "blue", False),    # R=0,8 + C=0,473 → ko'k, shtrixsiz
    (217.0, "auto_accredited", 3, 3, "red", False), # O3 ekstremal
])
def test_pending_review_flag(value, method, nsrc, rec, expected_zone, pending):
    ind = Indicator("pm25", value=value, norm=35.0, method=method, n_sources=nsrc, recency_days=rec)
    res = compute_facility([ind])
    assert res["zone"] == expected_zone
    assert res["pending_review"] is pending


# ---------- C komponentlari (§5.2) ----------
@pytest.mark.parametrize("days,expected", [
    (0, 1.0), (7, 1.0), (8, 0.7), (30, 0.7), (31, 0.3), (90, 0.3), (91, 0.0), (365, 0.0),
])
def test_f_recency(days, expected):
    assert f_recency(days) == expected


@pytest.mark.parametrize("n,expected", [(0, 0.0), (1, 1 / 3), (2, 2 / 3), (3, 1.0), (10, 1.0)])
def test_f_redundancy(n, expected):
    assert f_redundancy(n) == pytest.approx(expected)


@pytest.mark.parametrize("method,expected", [
    ("auto_accredited", 1.0), ("auto", 1.0), ("semi", 0.7), ("self_report", 0.4),
    ("citizen", 0.2), ("unknown", 0.0),
])
def test_f_method(method, expected):
    assert f_method(method) == expected


@pytest.mark.parametrize("av,pl,expected", [(1, 1, 1.0), (1, 2, 0.5), (2, 2, 1.0), (3, 2, 1.0), (0, 5, 0.0)])
def test_f_completeness(av, pl, expected):
    assert f_completeness(av, pl) == expected


def test_confidence_full_formula():
    """C = 0,30·1,0 + 0,25·(2/3) + 0,25·1,0 + 0,20·0,5 = 0,8167 → 0,817"""
    ind = Indicator("pm25", 20.0, 35.0, method="auto_accredited", n_sources=2, recency_days=5)
    assert ind.confidence(available=1, planned=2) == pytest.approx(0.817, abs=1e-3)


def test_confidence_o6_reduces_by_point_two():
    ind = Indicator("pm25", 20.0, 35.0, method="auto_accredited", n_sources=3, recency_days=5)
    c_full = ind.confidence(1, 1, station_far_from_industry=False)
    c_far = ind.confidence(1, 1, station_far_from_industry=True)
    assert c_far == pytest.approx(c_full - 0.2)
    assert c_far >= 0.0


# ---------- severity (§5.4) ----------
@pytest.mark.parametrize("R,sev", [
    (0.5, 1), (1.0, 1), (2.0, 1), (2.001, 2), (3.0, 2), (5.0, 2), (5.001, 3), (50.0, 3), (None, None),
])
def test_severity_scale(R, sev):
    assert severity_of(R) == sev


# ---------- override qoidalar (§5.3) ----------
def _mk_auto(value, norm=35.0, n=3, days=3, code="pm25"):
    return Indicator(code, value, norm, method="auto_accredited", n_sources=n, recency_days=days)


def test_o1_two_indicators_step_up_yellow_to_red():
    res = compute_facility([_mk_auto(45.5), _mk_auto(8.4, norm=6.0, code="bod")], planned_indicators=2)
    assert res["zone"] == "red" and "O1" in res["overrides"]
    assert res["severity"] == 1  # severity faqat R ga bog'liq (§5.4)


def test_o1_single_indicator_no_override():
    """Bitta indikator oshsa — O1 ishlamaydi (faqat 2+ indikator)."""
    res = compute_facility([_mk_auto(49.0)], planned_indicators=2)
    assert res["zone"] == "yellow" and "O1" not in res["overrides"]


def test_o1_impossible_from_green():
    """Barcha R≤1 bo'lsa O1 trigger bo'lmaydi (primary R = max R)."""
    res = compute_facility([_mk_auto(28.0), _mk_auto(4.2, norm=6.0, code="bod")], planned_indicators=2)
    assert res["zone"] == "green" and "O1" not in res["overrides"]


def test_o2_confirmed_appeal_at_least_yellow():
    res = compute_facility([_mk_auto(28.0)], appeal_confirmed=True)
    assert res["zone"] == "yellow" and "O2" in res["overrides"]


def test_o2_red_stays_red():
    res = compute_facility([_mk_auto(84.0)], appeal_confirmed=True)
    assert res["zone"] == "red"


def test_o3_extreme_value_red():
    res = compute_facility([_mk_auto(217.0)])
    assert res["zone"] == "red" and res["severity"] == 3 and "O3" in res["overrides"]


def test_o4_systemic_flag():
    res = compute_facility([_mk_auto(77.0)], seasonal_3y=True)
    assert res["systemic"] is True and "O4" in res["overrides"] and res["zone"] == "red"


def test_o5_natural_source_keeps_color():
    res = compute_facility([_mk_auto(108.5)], natural_source=True)
    assert res["zone"] == "red" and "O5" in res["overrides"]     # yashilga o'tkazilmaydi!
    assert any("tabiiy manba" in r for r in res["reasons"])


def test_o6_station_far_reduces_confidence():
    near = compute_facility([_mk_auto(28.0)])
    far = compute_facility([_mk_auto(28.0)], station_far_from_industry=True)
    assert far["C"] == pytest.approx(near["C"] - 0.2, abs=1e-6)
    assert "O6" in far["overrides"]


def test_no_data_blue():
    res = compute_facility([Indicator("pm25", None, 35.0)])
    assert res["zone"] == "blue" and res["R"] is None


def test_rule_version_present():
    res = compute_facility([_mk_auto(28.0)])
    assert res["rule_version"] == "1.0"


# ---------- agregatsiya (§5.5) ----------
def _c(zone, severity=2, C=0.7):
    return {"zone": zone, "severity": severity, "C": C}


@pytest.mark.parametrize("classes,coverage,expected", [
    ([_c("red", 2, 0.7), _c("green")], 0.9, "red"),                       # qoida 1
    ([_c("red", 1, 0.7), _c("green")], 0.9, "yellow"),                    # severity<2 → tasdiqlash
    ([_c("red", 2, 0.4), _c("green")], 0.9, "yellow"),                    # C<0,5 → tasdiqlash
    ([_c("yellow"), _c("yellow")], 0.9, "red"),                           # ≥2 sariq
    ([_c("yellow"), _c("green"), _c("green")], 1.0, "yellow"),            # bitta sariq
    ([_c("green"), _c("green")], 0.9, "green"),                           # hammasi yashil + qamrov ok
    ([_c("green"), _c("green")], 0.5, "blue"),                            # qamrov < 70%
    ([], 1.0, "blue"),                                                    # bo'sh
    ([_c("blue")], 1.0, "blue"),                                          # faqat ko'k
])
def test_aggregate_zone(classes, coverage, expected):
    assert aggregate_zone(classes, coverage) == expected
