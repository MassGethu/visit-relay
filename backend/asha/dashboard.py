"""Dashboard views for the ANM / PHC and the ASHA: pure functions over saved visits.

Nothing here interprets her health. It only sorts what was said:
  - danger flags already detected (a later "no" never clears one; only the ANM closes it)
  - visits due or overdue (her dictated date first, otherwise the usual gap for the visit type)
  - signs not asked last time ("not_checked" is never "no")
  - items to report to the ANM, and values to double-check (disputed signs, readings outside
    the speech-recognition guard ranges in numbers.PLAUSIBLE)
Trend chips say only Higher / Lower / Same, never "good" or "bad".
"""
from __future__ import annotations

import datetime as dt

from .danger import CORE_SIGNS, VISIT_GROUPS
from .numbers import PLAUSIBLE

REFERRAL_STEPS = ("flagged", "referred", "reached_phc", "closed")
MARK_KINDS = ("reported", "checked")
# Usual gap in days when she dictated no next-visit date. ANC is monthly, PNC / HBNC follow the
# day 1, 3, 7, 14, 21, 28, 42 schedule (about weekly), HBYC is every three months.
USUAL_GAP = {"anc": 30, "pnc": 7, "hbnc": 7, "hbyc": 90}
SOON_DAYS = 3
RECENT_DAYS = 30
WEEK_DAYS = 7
TREND_FIELDS = ("weight_kg", "hb", "bp")


def day(value: str | dt.date | None) -> dt.date | None:
    if value is None or isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def flag_key(visit_id: int, sign: str) -> str:
    return f"flag:{visit_id}:{sign}"


def concern_key(visit_id: int, index: int) -> str:
    return f"concern:{visit_id}:{index}"


def check_key(visit_id: int, what: str) -> str:
    return f"check:{visit_id}:{what}"


# ---------- due dates ----------

def last_visit_date(patient: dict, visits: list[dict]) -> dt.date | None:
    """Newest saved visit, else the synthetic seed in beneficiaries.json."""
    dates = [day(v["saved_at"]) for v in visits] + [day((patient.get("last_visit") or {}).get("date"))]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def due_status(patient: dict, visits: list[dict], today: dt.date) -> dict:
    last = last_visit_date(patient, visits)
    dictated = day((visits[0]["record"] or {}).get("next_visit_date")) if visits else None
    if dictated and last and dictated >= last:
        due, basis = dictated, "dictated"
    elif last:
        due, basis = last + dt.timedelta(days=USUAL_GAP.get(patient.get("visit_type"), 30)), "usual_gap"
    else:
        return {"state": "unknown", "date": None, "days": None, "basis": None, "last": None}
    days = (due - today).days
    state = "overdue" if days < 0 else "today" if days == 0 else "soon" if days <= SOON_DAYS else "later"
    return {"state": state, "date": due.isoformat(), "days": days, "basis": basis, "last": last.isoformat()}


# ---------- danger flags ----------

def danger_flags(patient: dict, visits: list[dict], referrals: dict, marks: dict) -> list[dict]:
    """Every sign marked present at any visit. referrals: {flag_key: [{"step", "at"}, ...]} oldest first."""
    flags = []
    for visit in visits:
        for row in visit["receipt"] or []:
            if row.get("status") != "present":
                continue
            key = flag_key(visit["id"], row["sign"])
            steps = referrals.get(key, [])
            flags.append({
                "key": key, "patient_id": patient["id"], "patient": patient["name"],
                "village": patient.get("village"), "visit_id": visit["id"], "visit_type": visit["visit_type"],
                "at": visit["saved_at"], "sign": row["sign"], "label": row.get("label") or row["sign"],
                "quote": row.get("quote"), "urgency": row.get("urgency"),
                "step": steps[-1]["step"] if steps else "flagged", "steps": steps,
                "reported": key in marks,
            })
    return flags


def next_step(step: str) -> str | None:
    i = REFERRAL_STEPS.index(step)
    return REFERRAL_STEPS[i + 1] if i + 1 < len(REFERRAL_STEPS) else None


# ---------- signs not asked ----------

def not_asked(visits: list[dict]) -> list[dict]:
    """Core signs of the visit type left "not_checked" at the newest visit, most urgent first."""
    if not visits:
        return []
    latest = visits[0]
    rows = {r["sign"]: r for r in latest["receipt"] or [] if r.get("status") == "not_checked"}
    core = [s for g in VISIT_GROUPS.get(latest["visit_type"], ()) for s in CORE_SIGNS.get(g, [])]
    order = [s for s in core if s in rows] or list(rows)      # unknown visit types keep every row
    return [{"sign": s, "label": rows[s].get("label") or s, "visit_id": latest["id"]} for s in order]


# ---------- review and double-check ----------

def concerns(patient: dict, visits: list[dict], marks: dict) -> list[dict]:
    items = []
    for visit in visits:
        for i, c in enumerate((visit["record"] or {}).get("worker_concerns") or []):
            if not c.get("flagged"):
                continue
            key = concern_key(visit["id"], i)
            items.append({"key": key, "kind": "concern", "patient_id": patient["id"], "patient": patient["name"],
                          "village": patient.get("village"), "visit_id": visit["id"], "at": c.get("at") or visit["saved_at"],
                          "quote": c.get("quote"), "reported": key in marks})
    return items


def _range(field: str, subject: str) -> tuple[str, tuple] | None:
    if field == "weight_kg":
        key = {"newborn": "weight_newborn", "mother": "weight_mother"}.get(subject)
    else:
        key = {"hb": "hb", "breaths_per_min": "breaths_per_min"}.get(field)
    return (key, PLAUSIBLE[key]) if key else None


def odd_values(record: dict, subject: str) -> list[tuple[str, object]]:
    """Readings outside the guard ranges: most likely a mis-heard number, so a person re-checks them."""
    out = []
    for field, value in record.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        guard = _range(field, subject)
        if guard and not guard[1][0] <= value <= guard[1][1]:
            out.append((field, value))
    bp = record.get("bp")
    if isinstance(bp, (list, tuple)) and len(bp) == 2:
        (s_lo, s_hi), (d_lo, d_hi) = PLAUSIBLE["systolic"], PLAUSIBLE["diastolic"]
        if not (s_lo <= bp[0] <= s_hi and d_lo <= bp[1] <= d_hi):
            out.append(("bp", list(bp)))
    temp = record.get("temperature")
    if isinstance(temp, (list, tuple)) and len(temp) == 2:
        lo, hi = PLAUSIBLE["temperature_c" if str(temp[1]).upper().startswith("C") else "temperature_f"]
        if not lo <= temp[0] <= hi:
            out.append(("temperature", list(temp)))
    return out


def double_checks(patient: dict, visits: list[dict], marks: dict) -> list[dict]:
    items = []
    for visit in visits:
        base = {"patient_id": patient["id"], "patient": patient["name"], "village": patient.get("village"),
                "visit_id": visit["id"], "at": visit["saved_at"]}
        for row in visit["receipt"] or []:
            if row.get("disputed") or row.get("needs_confirmation"):
                key = check_key(visit["id"], row["sign"])
                items.append({**base, "key": key, "kind": "disputed_sign", "sign": row["sign"],
                              "label": row.get("label") or row["sign"], "status": row.get("status"),
                              "quote": row.get("quote"), "checked": key in marks})
        for field, value in odd_values(visit["record"] or {}, patient.get("subject", "")):
            key = check_key(visit["id"], field)
            items.append({**base, "key": key, "kind": "odd_value", "field": field, "value": value,
                          "checked": key in marks})
    return items


# ---------- timeline ----------

def timeline(patient: dict, visits: list[dict]) -> dict:
    """{field: {"points": [{"date", "value"}], "direction": higher|lower|same|None}}, oldest first."""
    out = {}
    seed = patient.get("last_visit") or {}
    for field in TREND_FIELDS:
        points = [{"date": v["saved_at"][:10], "value": v["record"][field]}
                  for v in reversed(visits) if (v["record"] or {}).get(field) is not None]
        if seed.get(field) is not None and (not points or seed["date"] < points[0]["date"]):
            points.insert(0, {"date": seed["date"], "value": seed[field], "seed": True})
        if not points:
            continue
        direction = None
        if len(points) > 1:
            before, after = points[-2]["value"], points[-1]["value"]
            if field == "bp":
                before, after = before[0], after[0]       # systolic leads the chip; both are shown
            direction = "higher" if after > before else "lower" if after < before else "same"
        out[field] = {"points": points, "direction": direction}
    return out


# ---------- whole views ----------

def patient_summary(patient: dict, visits: list[dict], referrals: dict, marks: dict, today: dt.date) -> dict:
    flags = danger_flags(patient, visits, referrals, marks)
    review = [f for f in flags if not f["reported"]] + [c for c in concerns(patient, visits, marks) if not c["reported"]]
    checks = [c for c in double_checks(patient, visits, marks) if not c["checked"]]
    due = due_status(patient, visits, today)
    asked = not_asked(visits)
    open_flags = [f for f in flags if f["step"] != "closed"]
    tags = [t for t, on in (("due_today", due["state"] == "today"), ("overdue", due["state"] == "overdue"),
                            ("danger", bool(open_flags)), ("not_asked", bool(asked)),
                            ("needs_review", bool(review or checks))) if on]
    return {"patient": patient, "due": due, "flags": flags, "open_flags": open_flags, "not_asked": asked,
            "review": review, "checks": checks, "tags": tags, "visit_count": len(visits)}


def village_summary(summaries: list[dict], histories: dict, today: dt.date) -> list[dict]:
    villages: dict[str, dict] = {}
    for s in summaries:
        p = s["patient"]
        v = villages.setdefault(p.get("village") or "—", {"village": p.get("village") or "—", "patients": 0,
                                                          "visits_this_week": 0, "visited_30_days": 0, "open_flags": 0})
        v["patients"] += 1
        v["open_flags"] += len(s["open_flags"])
        visits = histories.get(p["id"], [])
        v["visits_this_week"] += sum(1 for x in visits if 0 <= (today - day(x["saved_at"])).days < WEEK_DAYS)
        last = last_visit_date(p, visits)
        if last and (today - last).days <= RECENT_DAYS:
            v["visited_30_days"] += 1
    return sorted(villages.values(), key=lambda v: (-v["open_flags"], v["village"]))


def search_entry(s: dict) -> dict:
    p = s["patient"]
    return {k: p.get(k) for k in ("id", "name", "village", "subject", "visit_type", "relation", "relation_name")} | {
        "spoken_names": p.get("spoken_names", []), "tags": s["tags"], "due": s["due"],
        "open_flags": len(s["open_flags"])}


def dashboard(patients: list[dict], histories: dict, referrals: dict, marks: dict, today: dt.date) -> dict:
    summaries = [patient_summary(p, histories.get(p["id"], []), referrals, marks, today) for p in patients]
    tags = {t: sum(t in s["tags"] for s in summaries)
            for t in ("due_today", "overdue", "danger", "not_asked", "needs_review")}
    newest = lambda item: item["at"]          # noqa: E731
    return {
        "today": today.isoformat(),
        "tags": tags,
        "report": sorted((i for s in summaries for i in s["review"]), key=newest, reverse=True),
        "checks": sorted((i for s in summaries for i in s["checks"]), key=newest, reverse=True),
        "flags": sorted((f for s in summaries for f in s["open_flags"]),
                        key=lambda f: (REFERRAL_STEPS.index(f["step"]), f["at"])),
        "villages": village_summary(summaries, histories, today),
        "patients": [search_entry(s) for s in summaries],
    }
