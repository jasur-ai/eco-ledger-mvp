# -*- coding: utf-8 -*-
"""MUROJAAT MODULI — TZ §6.1–§6.6 ning implementatsiyasi.

Tamoyillar:
  * 7 holatli zanjir; har o'tish `appeal_events` ga (append-only) yoziladi.
  * SLA: qabul → birinchi javob ≤ 10 ish kuni (jurnalist — 5 ish kuni).
  * Dublikat: trigramma(Dice) ≥ 0,85 + ≤300 m + ≤24 soat + bir xil kategoriya → birlashtirish.
    0,55–0,85 → "o'xshash murojaatlar" guruhi (e'lon kechiktirilmaydi).
  * Anti-spam faqat texnik: bitta telefon → kuniga ≤ 5 murojaat.
  * O'CHIRISH YO'Q: delete() ataylab xato beradi (TZ §6.5 — "o'chirishga urinish rad etiladi").
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta, timezone


def _now():
    """Naive UTC vaqti (SQLite matn formatiga mos)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from .. import config
from ..db import add_event, audit

STATUSES = ("yuborildi", "ko'rib_chiqilmoqda", "tashkilotga_yuborildi",
            "javob_berildi", "hal_qilindi", "rad_etildi", "apellyatsiya")

# Ruxsat etilgan o'tishlar: (from, to) -> ruxsat etilgan actorlar to'plami
TRANSITIONS = {
    ("yuborildi", "ko'rib_chiqilmoqda"): {"system", "operator"},
    ("ko'rib_chiqilmoqda", "tashkilotga_yuborildi"): {"operator"},
    ("tashkilotga_yuborildi", "javob_berildi"): {"operator"},
    ("javob_berildi", "hal_qilindi"): {"operator"},
    ("javob_berildi", "rad_etildi"): {"operator"},
    ("rad_etildi", "apellyatsiya"): {"citizen"},
    ("apellyatsiya", "ko'rib_chiqilmoqda"): {"system", "operator"},
    ("ko'rib_chiqilmoqda", "javob_berildi"): {"operator"},   # apellyatsiyadan keyingi yakun
    ("tashkilotga_yuborildi", "hal_qilindi"): {"operator"},  # tezkor hal (dalil bilan)
}
FINAL = {"hal_qilindi"}

CATEGORIES = ("air", "water", "waste", "noise", "odor", "soil", "other")
TYPES = ("T1", "T2", "T3", "T4", "T5")
CONSENT = ("full_name", "partial", "anonymous")
AUTHOR_KINDS = ("individual", "legal", "journalist", "anonymous", "facility")

DUP_STRONG = 0.85
DUP_WEAK = 0.55
DUP_RADIUS_M = 300.0
DUP_WINDOW_H = 24
MAX_PER_DAY = 5


# ---------- yordamchilar ----------
def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _trigrams(text: str) -> set[str]:
    t = " ".join((text or "").lower().split())
    if len(t) < 3:
        return {t} if t else set()
    return {t[i:i + 3] for i in range(len(t) - 2)}


def trigram_similarity(a: str, b: str) -> float:
    """Dice koeffitsiyenti (0–1)."""
    A, B = _trigrams(a), _trigrams(b)
    if not A or not B:
        return 0.0
    return 2 * len(A & B) / (len(A) + len(B))


def add_workdays(start: datetime, days: int) -> datetime:
    """Ish kunlari (Sh/Ya hisobga olinmaydi; bayramlar MVP'da soddalashtirilgan)."""
    d, left = start, days
    while left > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return d


def _ts(dt: datetime | None = None) -> str:
    return (dt or _now()).strftime("%Y-%m-%d %H:%M:%S")


class AppealError(ValueError):
    pass


class AppealService:
    def __init__(self, conn):
        self.conn = conn

    # ---------------- yaratish ----------------
    def create(self, *, description: str, category: str, lat: float, lon: float,
               appeal_type: str = "T1", eco_id: str | None = None, zone_id: str | None = None,
               occurred_at: str | None = None, phone: str | None = None,
               author_kind: str = "individual", publication_consent: str = "partial",
               report_to_authority: bool = True, lang: str = "uz",
               responsible_body: str | None = None, now: datetime | None = None) -> dict:
        # --- validatsiya (12 maydon, §6.4) ---
        if not description or not (30 <= len(description) <= 2000):
            raise AppealError("Tavsif 30–2000 belgi bo'lishi kerak")
        if category not in CATEGORIES:
            raise AppealError(f"Kategoriya noto'g'ri: {category}")
        if appeal_type not in TYPES:
            raise AppealError(f"Murojaat turi noto'g'ri: {appeal_type}")
        if author_kind not in AUTHOR_KINDS:
            raise AppealError(f"Muallif turi noto'g'ri: {author_kind}")
        if publication_consent not in CONSENT:
            raise AppealError("Oshkoralik roziligi noto'g'ri")
        if author_kind != "anonymous" and not phone:
            raise AppealError("Telefon tasdiqlanishi shart (anonimdan tashqari)")
        if author_kind == "anonymous" and eco_id:
            raise AppealError("Anonim murojaat faqat hudud darajasida (korxona nomiga emas)")
        now = now or _now()

        # --- anti-spam (faqat texnik) ---
        if phone:
            day = now.strftime("%Y-%m-%d")
            cnt = self.conn.execute(
                "SELECT COUNT(*) FROM appeals WHERE author_phone=? AND created_at LIKE ?",
                (phone, day + "%")).fetchone()[0]
            if cnt >= MAX_PER_DAY:
                raise AppealError(f"Anti-spam: bitta telefonga kuniga ≤{MAX_PER_DAY} murojaat")

        # --- dublikat: ikki pog'onali ---
        similar_group = None
        merged_into = None
        rows = self.conn.execute(
            "SELECT * FROM appeals WHERE category=? AND created_at >= ?",
            (category, _ts(now - timedelta(hours=DUP_WINDOW_H)))).fetchall()
        for r in rows:
            dist = haversine_m(lat, lon, r["lat"], r["lon"])
            if dist > DUP_RADIUS_M:
                continue
            sim = trigram_similarity(description, r["description"])
            if sim >= DUP_STRONG:
                # birlashtirish: yangi murojaat YO'QOLMAYDI — qo'shiladi
                self.conn.execute(
                    "UPDATE appeals SET supporters_count = supporters_count + 1, updated_at=? "
                    "WHERE appeal_id=?", (_ts(now), r["appeal_id"]))
                self.conn.execute(
                    "INSERT INTO appeal_events(appeal_id, from_status, to_status, actor, comment, ts) "
                    "VALUES (?,?,?,?,?,?)",
                    (r["appeal_id"], r["status"], r["status"], "system",
                     f"Yangi murojaat birlashtirildi (o'xshashlik {sim:.2f})", _ts(now)))
                audit(self.conn, "appeal", r["public_code"], "merged",
                      payload={"similarity": round(sim, 3), "distance_m": round(dist, 1)})
                self.conn.commit()
                return {"merged_into": r["public_code"], "similarity": round(sim, 3),
                        "supporters_count": r["supporters_count"] + 1}
            if sim >= DUP_WEAK:
                similar_group = similar_group or f"G-{uuid.uuid4().hex[:8]}"

        # --- SLA muddati ---
        days = config.SLA_WORKDAYS_JOURNALIST if author_kind == "journalist" else config.SLA_WORKDAYS
        deadline = add_workdays(now, days)

        code = f"A-{now.year}-{self.conn.execute('SELECT COUNT(*) + 1 FROM appeals').fetchone()[0]:06d}"
        cur = self.conn.execute(
            """INSERT INTO appeals(public_code, appeal_type, category, eco_id, zone_id, lat, lon,
               description, occurred_at, status, responsible_body, sla_deadline, author_phone,
               author_kind, publication_consent, report_to_authority, lang, similar_group,
               created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (code, appeal_type, category, eco_id, zone_id, lat, lon, description, occurred_at,
             "yuborildi", responsible_body or "Ekologiya va iqlim o'zgarishi milliy qo'mitasi "
             "(hududiy boshqarma)", _ts(deadline), phone, author_kind, publication_consent,
             1 if report_to_authority else 0, lang, similar_group, _ts(now), _ts(now)))
        aid = cur.lastrowid
        self.conn.execute(
            "INSERT INTO appeal_events(appeal_id, from_status, to_status, actor, comment, ts) "
            "VALUES (?,?,?,?,?,?)", (aid, None, "yuborildi", "citizen", "Murojaat qabul qilindi", _ts(now)))
        audit(self.conn, "appeal", code, "created", actor="citizen",
              payload={"type": appeal_type, "category": category, "sla_days": days})
        self.conn.commit()
        return self.get(code)

    # ---------------- holat o'tishi ----------------
    def transition(self, code: str, to_status: str, actor: str, comment: str | None = None,
                   evidence: str | None = None, now: datetime | None = None) -> dict:
        if to_status not in STATUSES:
            raise AppealError(f"Holat noto'g'ri: {to_status}")
        r = self.conn.execute("SELECT * FROM appeals WHERE public_code=?", (code,)).fetchone()
        if not r:
            raise AppealError(f"Murojaat topilmadi: {code}")
        if r["status"] in FINAL:
            raise AppealError("Yakunlangan murojaat o'zgartirilmaydi")
        allowed = TRANSITIONS.get((r["status"], to_status))
        if not allowed:
            raise AppealError(f"O'tish mumkin emas: {r['status']} → {to_status}")
        if actor not in allowed:
            raise AppealError(f"Aktor {actor} bu o'tishni qila olmaydi")
        if to_status == "rad_etildi" and not comment:
            raise AppealError("Rad etishda sabab MAJBURIY yoziladi")
        if to_status == "hal_qilindi" and not evidence:
            raise AppealError("Hal qilishda tasdiq (o'lchov/foto) MAJBURIY")
        now = now or _now()
        first_response = r["first_response_at"]
        if to_status == "javob_berildi" and not first_response:
            first_response = _ts(now)
        resolved = _ts(now) if to_status in FINAL else r["resolved_at"]
        self.conn.execute(
            "UPDATE appeals SET status=?, first_response_at=?, resolved_at=?, updated_at=? "
            "WHERE appeal_id=?",
            (to_status, first_response, resolved, _ts(now), r["appeal_id"]))
        self.conn.execute(
            "INSERT INTO appeal_events(appeal_id, from_status, to_status, actor, comment, evidence, ts) "
            "VALUES (?,?,?,?,?,?,?)",
            (r["appeal_id"], r["status"], to_status, actor, comment, evidence, _ts(now)))
        audit(self.conn, "appeal", code, f"status:{to_status}", actor=actor, payload={"evidence": evidence})
        self.conn.commit()
        return self.get(code)

    # ---------------- o'qish ----------------
    def get(self, code: str) -> dict:
        r = self.conn.execute("SELECT * FROM appeals WHERE public_code=?", (code,)).fetchone()
        if not r:
            raise AppealError(f"Murojaat topilmadi: {code}")
        d = dict(r)
        d["history"] = [dict(x) for x in self.conn.execute(
            "SELECT from_status, to_status, actor, comment, evidence, ts FROM appeal_events "
            "WHERE appeal_id=? ORDER BY id", (r["appeal_id"],))]
        return d

    def list_open(self, status: str | None = None) -> list[dict]:
        q = "SELECT * FROM appeals WHERE status NOT IN ('hal_qilindi')"
        args: tuple = ()
        if status:
            q += " AND status=?"
            args = (status,)
        return [dict(x) for x in self.conn.execute(q + " ORDER BY created_at", args)]

    # ---------------- SLA vasl / KPI ----------------
    def sla_report(self, now: datetime | None = None) -> dict:
        now = now or _now()
        rows = [dict(x) for x in self.conn.execute("SELECT * FROM appeals ORDER BY appeal_id")]
        answered, overdue, open_c = [], 0, 0
        for r in rows:
            created = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S")
            deadline = datetime.strptime(r["sla_deadline"], "%Y-%m-%d %H:%M:%S")
            if r["first_response_at"]:
                fr = datetime.strptime(r["first_response_at"], "%Y-%m-%d %H:%M:%S")
                answered.append((fr - created).total_seconds() / 86400)
            elif r["status"] not in FINAL:
                open_c += 1
                if now > deadline:
                    overdue += 1
        answered.sort()
        median = answered[len(answered) // 2] if answered else None
        return {
            "total": len(rows),
            "answered": len(answered),
            "open": open_c,
            "overdue": overdue,
            "median_response_days": round(median, 2) if median is not None else None,
            "compliance_pct": round(100.0 * sum(1 for d in answered if d <= config.SLA_WORKDAYS)
                                    / len(answered), 1) if answered else None,
            "overdue_pct": round(100.0 * overdue / open_c, 1) if open_c else 0.0,
        }

    def due_events(self, now: datetime | None = None) -> list[dict]:
        """7-kun ogohlantirish / 10-kun muddati o'tdi / 15-kun eskalatsiya (TZ §6.5)."""
        now = now or _now()
        out = []
        for r in self.list_open():
            created = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S")
            deadline = datetime.strptime(r["sla_deadline"], "%Y-%m-%d %H:%M:%S")
            age = (now - created).total_seconds() / 86400
            if now > deadline + timedelta(days=5):
                out.append({"code": r["public_code"], "kind": "escalate", "age_days": round(age, 1)})
            elif now > deadline:
                out.append({"code": r["public_code"], "kind": "overdue", "age_days": round(age, 1)})
            elif age >= config.SLA_WARN_DAY:
                out.append({"code": r["public_code"], "kind": "warn", "age_days": round(age, 1)})
        return out

    # ---------------- o'chirish — TAQIQLANGAN ----------------
    def delete(self, *_args, **_kwargs):
        raise PermissionError("Murojaatlarni o'chirish taqiqlangan: yozuvlar append-only "
                              "(TZ §6.5 — o'chirishga urinish rad etiladi)")
