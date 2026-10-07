# -*- coding: utf-8 -*-
"""ZONA DVIGATELI — TZ §5.1–§5.5 ning to'liq implementatsiyasi.

Qoidalar (rule_version = 1.0):
  R = V_measured / N_reference
  Asosiy rang:  qizil  R ≥ 2,0
                sariq  1,0 < R < 2,0
                yashil R ≤ 1,0  va  C ≥ 0,5
                ko'k   C < 0,5 yoki ma'lumot yo'q (⚠ "toza" degani EMAS)
  C = 0,30·f_recency + 0,25·f_redundancy + 0,25·f_method + 0,20·f_completeness
  Override: O1–O6 (§5.3); Severity: 1 (R≤2), 2 (2<R≤5), 3 (R>5) (§5.4)
"""
from __future__ import annotations

from dataclasses import dataclass, field

RULE_VERSION = "1.0"

W = {"recency": 0.30, "redundancy": 0.25, "method": 0.25, "completeness": 0.20}
METHOD_SCORES = {
    "auto_accredited": 1.0,   # akkreditatsiyalangan avtomatik stansiya/laboratoriya
    "auto": 1.0,
    "semi": 0.7,              # yarim avtomatik
    "self_report": 0.4,       # korxona o'z e'loni
    "citizen": 0.2,           # fuqaro signali (tasdiqlanmagan)
}
ZONES = ("red", "yellow", "green", "blue")
STEP_UP = {"green": "yellow", "yellow": "red", "red": "red", "blue": "blue"}
ZONE_RANK = {"blue": 0, "green": 1, "yellow": 2, "red": 3}

CUT_EXCEED = 1.0   # R > 1.0 — oshib ketish
CUT_RED = 2.0      # R ≥ 2.0 — qizil
CUT_C = 0.5        # C ≥ 0.5 — ishonchli ma'lumot


# ---------------- C komponentlari (§5.2) ----------------
def f_recency(days: int | None) -> float:
    if days is None:
        return 0.0
    if days <= 7:
        return 1.0
    if days <= 30:
        return 0.7
    if days <= 90:
        return 0.3
    return 0.0


def f_redundancy(n_sources: int) -> float:
    return min(1.0, max(0, n_sources) / 3.0)


def f_method(method: str) -> float:
    return METHOD_SCORES.get(method, 0.0)


def f_completeness(available: int, planned: int) -> float:
    if planned <= 0:
        return 1.0
    return min(1.0, max(0, available) / planned)


@dataclass
class Indicator:
    """Bitta indikator bo'yicha 30-kunlik o'rtacha o'lchov (§5.1)."""
    code: str
    value: float | None
    norm: float | None
    method: str = "self_report"
    n_sources: int = 1
    recency_days: int | None = 30

    @property
    def R(self) -> float | None:
        if self.value is None or not self.norm:
            return None
        return self.value / self.norm

    def confidence(self, available: int = 1, planned: int = 1,
                   station_far_from_industry: bool = False) -> float:
        c = (W["recency"] * f_recency(self.recency_days)
             + W["redundancy"] * f_redundancy(self.n_sources)
             + W["method"] * f_method(self.method)
             + W["completeness"] * f_completeness(available, planned))
        if station_far_from_industry:      # O6 — hudud chegarasi effekti
            c = max(0.0, c - 0.2)
        return round(c, 3)


def severity_of(R: float | None) -> int | None:
    """§5.4: 1 (R≤2), 2 (2<R≤5), 3 (R>5)."""
    if R is None:
        return None
    if R <= 2.0:
        return 1
    if R <= 5.0:
        return 2
    return 3


def base_zone(R: float | None, C: float) -> str:
    """§5.1 asosiy rang qoidasi (override'larsiz)."""
    if R is None:
        return "blue"                      # ma'lumot yo'q
    if C < CUT_C:
        return "blue"                      # past ishonch → neytral
    if R >= CUT_RED:
        return "red"
    if R > CUT_EXCEED:
        return "yellow"
    return "green"


def compute_facility(
    indicators: list[Indicator],
    planned_indicators: int | None = None,
    appeal_confirmed: bool = False,
    station_far_from_industry: bool = False,
    natural_source: bool = False,
    seasonal_3y: bool = False,
) -> dict:
    """Korxona darajasidagi klassni hisoblaydi (barcha §5 qoidalari bilan)."""
    planned = planned_indicators or max(1, len(indicators))
    available = sum(1 for i in indicators if i.value is not None)

    # Har bir indikator bo'yicha R va C
    per_indicator = []
    for ind in indicators:
        C_i = ind.confidence(available, planned, station_far_from_industry)
        per_indicator.append({"code": ind.code, "R": ind.R, "C": C_i,
                              "value": ind.value, "norm": ind.norm, "method": ind.method,
                              "n_sources": ind.n_sources})

    measured = [p for p in per_indicator if p["R"] is not None]
    reasons: list[str] = []
    overrides: list[str] = []

    if not measured:
        return {
            "zone": "blue", "severity": None, "R": None, "C": None, "indicator": None,
            "pending_review": False, "overrides": [], "per_indicator": per_indicator,
            "reasons": ["Ma'lumot yo'q — «toza» degani emas, tekshiruv talab qilinadi"],
            "rule_version": RULE_VERSION,
        }

    primary = max(measured, key=lambda p: p["R"])
    R, C = primary["R"], primary["C"]
    primary_code = primary["code"]          # R aynan qaysi indikatordan olingan (R58 tuzatishi)
    zone = base_zone(R, C)
    pending_review = (zone == "blue" and R > CUT_EXCEED)   # sariq shtrix: tekshiruv kutilmoqda

    if zone == "green":
        reasons.append(f"Norma ichida: R={R:.2f}, C={C:.2f} (ishonchli ma'lumot)")
    elif zone == "yellow":
        reasons.append(f"Normadan oshgan, lekin 2 baravardan kam: R={R:.2f}")
    elif zone == "red":
        reasons.append(f"Normadan 2 baravar va undan ko'p oshgan: R={R:.2f}")
    else:
        if primary["R"] is not None and R > CUT_EXCEED:
            reasons.append(f"Oshib ketish bor (R={R:.2f}), lekin ishonch past (C={C:.2f}) — "
                           f"rang ko'k, «tekshiruv kutilmoqda» shtrixi bilan")
        else:
            reasons.append(f"Ma'lumot yetarli emas (C={C:.2f}) — ko'k-neytral")

    # ---- O1: ko'p indikatorli oshib ketish ----
    n_over = sum(1 for p in measured if p["R"] > CUT_EXCEED)
    if n_over >= 2 and zone in ("green", "yellow"):
        zone = STEP_UP[zone]
        overrides.append("O1")
        reasons.append(f"O1: {n_over} indikatorda R>1 — rang bir pog'ona yuqoriga ko'tarildi")

    # ---- O2: tasdiqlangan murojaat ----
    if appeal_confirmed and zone in ("green", "yellow"):
        zone = "yellow"
        overrides.append("O2")
        reasons.append("O2: tasdiqlangan murojaat — kamida sariq")
    elif appeal_confirmed:
        overrides.append("O2")
        reasons.append("O2: tasdiqlangan murojaat hisobga olindi (rang o'zgarmadi)")

    # ---- O3: ekstremal qiymat ----
    if R >= 5.0:
        zone = "red"
        overrides.append("O3")
        reasons.append("O3: R ≥ 5 — birinchi navbatda tekshiruv")

    # ---- O4 / O5 / O6 ----
    systemic = False
    if seasonal_3y:
        systemic = True
        overrides.append("O4")
        reasons.append("O4: 3 yil ketma-ket shu oyda R>2 — tizimli (mavsumiy) holat, ayblov emas")
    if natural_source:
        overrides.append("O5")
        reasons.append("O5: tabiiy manba (chang bo'roni/transchegaraviy) — rang saqlanadi, "
                       "yashilga o'tkazilmaydi")
    if station_far_from_industry:
        overrides.append("O6")
        reasons.append("O6: stansiya sanoat zonasidan uzoq — C pasaytirildi")

    return {
        "zone": zone, "indicator": primary_code,
        "severity": severity_of(R),
        "R": round(R, 3),
        "C": C,
        "pending_review": pending_review,
        "overrides": overrides,
        "systemic": systemic,
        "per_indicator": per_indicator,
        "reasons": reasons,
        "rule_version": RULE_VERSION,
    }


# ---------------- §5.5 — korxonadan zonaga agregatsiya ----------------
def aggregate_zone(classes: list[dict], coverage: float) -> str:
    """classes — compute_facility natijalari; coverage — haqiqiy o'lchovli obyektlar ulushi (0–1)."""
    if not classes:
        return "blue"
    if any(c["zone"] == "red" and (c["severity"] or 0) >= 2 and (c["C"] or 0) >= CUT_C
           for c in classes):
        return "red"
    if sum(1 for c in classes if c["zone"] == "yellow") >= 2:
        return "red"
    if any(c["zone"] == "yellow" for c in classes):
        return "yellow"
    if any(c["zone"] == "red" for c in classes):
        return "yellow"           # red bor, lekin C<0,5 yoki severity<2 — tasdiqlash kerak
    if (all(c["zone"] == "green" for c in classes) and (coverage or 0) >= 0.70):
        return "green"
    return "blue"                 # jumladan: qamrov < 70%
