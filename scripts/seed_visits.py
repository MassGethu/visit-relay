"""Fill the encrypted store with SYNTHETIC visits so the dashboard has something to show.

    python scripts/seed_visits.py        # only into an empty store
    python scripts/delete_all.py --yes && python scripts/seed_visits.py   # start again

Every visit is made up. Danger receipts come from the real rules checker reading made-up English
notes, so flags, "not asked" signs and labels look exactly like a dictated visit.
Dates are relative to today, so "due today" and "overdue" always have examples.
"""
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from asha.danger import DangerChecker, sign_label  # noqa: E402
from store import default_store  # noqa: E402

TODAY = dt.date.today()


def at(days_ago: int, hour: int = 10) -> str:
    return dt.datetime.combine(TODAY - dt.timedelta(days=days_ago), dt.time(hour)).isoformat(timespec="seconds")


def date_in(days: int) -> str:
    return (TODAY + dt.timedelta(days=days)).isoformat()


# (patient, visit type, days ago, notes, record, extra): extra may hold "concern", "disputed" (a sign),
# "steps" (referral steps after the flag) and "reported" (marked as reported to the ANM).
VISITS = [
    ("4127", "anc", 28, ["No bleeding. No fever."],
     {"gestational_month": 6, "weight_kg": 53.0, "hb": 10.8, "bp": [110, 70], "ifa_taking": True}, {}),
    ("4127", "anc", 6, ["No bleeding.", "She has severe headache and blurred vision."],
     {"gestational_month": 7, "weight_kg": 54.2, "hb": 10.4, "bp": [118, 76], "ifa_taking": True,
      "next_visit_date": date_in(0)}, {}),
    ("4381", "anc", 35, ["No bleeding."],
     {"gestational_month": 5, "weight_kg": 49.0, "hb": 11.2, "bp": [108, 72], "next_visit_date": date_in(-5)}, {}),
    ("5096", "anc", 3, ["She has bleeding from vagina since morning."],
     {"gestational_month": 8, "weight_kg": 520, "hb": 9.6, "bp": [122, 80]},
     {"concern": "She looks very tired and worried about the delivery.", "steps": ["referred"]}),
    ("5274", "anc", 20, ["No fever. No swelling on face."],
     {"gestational_month": 4, "weight_kg": 51.0, "hb": 11.5, "bp": [112, 74]}, {}),
    ("6248", "pnc", 2, ["She has fever since two days."],
     {"weight_kg": 54.0, "temperature": [100.4, "F"], "next_visit_date": date_in(1)}, {"disputed": "pnc_fever"}),
    ("6735", "pnc", 9, ["No fever."], {"weight_kg": 57.0}, {}),
    ("7409", "hbnc", 8, ["No fever. Baby is feeding well."], {"weight_kg": 2.8}, {}),
    ("7409", "hbnc", 1, ["Baby is not feeding well."],
     {"weight_kg": 2.7, "next_visit_date": date_in(2)}, {"steps": ["referred", "reached_phc"]}),
    ("8031", "hbnc", 12, ["Baby has fever."], {"weight_kg": 2.6},
     {"steps": ["referred", "reached_phc", "closed"], "reported": True}),
    ("8031", "hbnc", 4, ["No convulsions, baby is breathing fast."],
     {"weight_kg": 28, "breaths_per_min": 68}, {}),
    ("8574", "hbyc", 2, ["No convulsions."], {"weight_kg": 8.9, "vaccinations_given": ["measles"]}, {}),
    ("9142", "hbyc", 40, ["Child has fast breathing."], {"weight_kg": 10.6, "breaths_per_min": 52},
     {"reported": True, "steps": ["referred"]}),
]


def receipt(kind: str, notes: list[str], when: str, disputed: str | None) -> tuple[list, list]:
    checker = DangerChecker(kind, tested_languages=("hi", "en"))
    for note in notes:
        checker.add_utterance(note, "en-IN")
    rows = [{**row, "label": sign_label(row["sign"]), "disputed": row["disputed"] or row["sign"] == disputed}
            for row in checker.receipt()]
    flags = [{"sign": r["sign"], "quote": r["quote"], "at": when, "by": "rules"}
             for r in rows if r["status"] == "present"]
    return rows, flags


def main() -> None:
    store = default_store()
    if store is None:
        sys.exit("DB_KEY is missing in .env; nothing was written.")
    patients = {p["id"]: p for p in json.loads((ROOT / "backend" / "data" / "beneficiaries.json").read_text())}
    if any(store.history(pid) for pid in patients):
        sys.exit("The store already has visits. Run `python scripts/delete_all.py --yes` first.")
    for pid, kind, days_ago, notes, record, extra in VISITS:
        assert patients[pid]["synthetic"], pid
        when = at(days_ago)
        rows, flags = receipt(kind, notes, when, extra.get("disputed"))
        concerns = [{"quote": extra["concern"], "at": when, "flagged": True}] if extra.get("concern") else []
        if concerns:
            record = {**record, "worker_concerns": concerns}
        visit_id = store.save_visit(
            beneficiary_id=pid, visit_type=kind, lang="en", saved_at=when, record=record,
            transcript=[{"text": n, "lang": "en"} for n in notes], receipt=rows, flags=flags, concerns=concerns)
        for f in flags:
            key = f"flag:{visit_id}:{f['sign']}"
            for i, step in enumerate(extra.get("steps", [])):
                store.add_referral_step(key, step, at(days_ago, 12 + i))
            if extra.get("reported"):
                store.mark(key, "reported", at(days_ago, 11))
        print(f"visit {visit_id}: {patients[pid]['name']} ({kind}, {days_ago} days ago), "
              f"{len(flags)} danger flag(s)")
    store.close()
    print("Synthetic visits saved.")


if __name__ == "__main__":
    main()
