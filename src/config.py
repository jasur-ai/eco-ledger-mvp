# -*- coding: utf-8 -*-
"""Ochiq-Eko-Ledger MVP — konfiguratsiya."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("ECO_LEDGER_DB") or os.path.join(BASE_DIR, "data", "eco_ledger.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
WEB_MAP = os.path.join(BASE_DIR, "web", "map.html")

RULE_VERSION = "1.0"          # TZ §5.1 qoida versiyasi
SLA_WORKDAYS = 10             # TZ §6.5 — qabul → birinchi javob
SLA_WORKDAYS_JOURNALIST = 5   # tezlashtirilgan rejim
SLA_WARN_DAY = 7
SLA_ESCALATE_DAY = 15
RULE_REVIEW_DAYS = 30         # rad etilgandan keyin apellyatsiya oynasi

# — Normativlar (TZ §4.2; SanQvaM 0053-23, 26-son qoida) —
NORMS = [
    {"indicator": "pm25", "kind": "one_time", "value": 35.0, "unit": "µg/m³",
     "basis": "SanQvaM 0053-23 (27.05.2024 tahriri)",
     "valid_from": "2024-05-27",
     "note": "JSST etaloni (2021): yillik 5 µg/m³ — faqat yorliq uchun, rang berishda ishlatilmaydi (TZ §5.6)."},
    {"indicator": "pm10", "kind": "one_time", "value": 500.0, "unit": "µg/m³",
     "basis": "SanQvaM 0053-23", "valid_from": "2024-05-27", "note": None},
    {"indicator": "co", "kind": "one_time", "value": 5.0, "unit": "mg/m³",
     "basis": "SanQvaM 0053-23", "valid_from": "2024-05-27", "note": None},
    {"indicator": "bod", "kind": "discharge", "value": 6.0, "unit": "mgO₂/dm³",
     "basis": "26-son sanitariya qoidalari (22.11.2024)", "valid_from": "2024-11-22",
     "note": "KBS/BOD-5; KOD/BXO uchun 30 mgO₂/dm³"},
    {"indicator": "kod", "kind": "discharge", "value": 30.0, "unit": "mgO₂/dm³",
     "basis": "26-son sanitariya qoidalari (22.11.2024)", "valid_from": "2024-11-22", "note": None},
]
WHO_PM25_ANNUAL = 15.0  # yorliq uchun (µg/m³, 24-soat)
