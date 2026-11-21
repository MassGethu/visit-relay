import datetime as dt

from asha import dashboard as d

TODAY = dt.date(2026, 11, 22)
MOTHER = {"id": "4127", "name": "Kavya Gowda", "subject": "mother", "visit_type": "anc", "village": "Hosahalli",
          "last_visit": {"date": "2026-10-24", "weight_kg": 52.0}}


def visit(vid, date, record=None, receipt=None, kind="anc"):
    return {"id": vid, "visit_type": kind, "saved_at": f"{date}T10:00:00", "record": record or {},
            "receipt": receipt or []}


def row(sign, status, **extra):
    return {"sign": sign, "label": sign.title(), "status": status, "quote": "synthetic words", **extra}


def test_dictated_next_visit_date_sets_the_due_date():
    visits = [visit(2, "2026-11-10", {"next_visit_date": "2026-11-22"})]

    due = d.due_status(MOTHER, visits, TODAY)

    assert due == {"state": "today", "date": "2026-11-22", "days": 0, "basis": "dictated", "last": "2026-11-10"}


def test_without_a_dictated_date_the_usual_gap_is_used_from_the_seed():
    due = d.due_status(MOTHER, [], TODAY)

    assert due["basis"] == "usual_gap" and due["date"] == "2026-11-23" and due["state"] == "soon"


def test_a_missed_due_date_is_overdue():
    due = d.due_status(MOTHER, [visit(1, "2026-10-01", {"next_visit_date": "2026-11-01"})], TODAY)

    assert due["state"] == "overdue" and due["days"] == -21


def test_a_later_no_never_clears_an_earlier_danger_flag():
    visits = [visit(2, "2026-11-20", receipt=[row("bleeding", "ruled_out")]),
              visit(1, "2026-11-01", receipt=[row("bleeding", "present")])]

    summary = d.patient_summary(MOTHER, visits, {}, {}, TODAY)

    assert [f["key"] for f in summary["open_flags"]] == ["flag:1:bleeding"]
    assert "danger" in summary["tags"]


def test_only_a_closed_referral_removes_a_flag_from_the_open_list():
    visits = [visit(1, "2026-11-01", receipt=[row("bleeding", "present")])]
    steps = {"flag:1:bleeding": [{"step": "referred", "at": "x"}, {"step": "closed", "at": "y"}]}

    summary = d.patient_summary(MOTHER, visits, steps, {}, TODAY)

    assert summary["flags"][0]["step"] == "closed" and summary["open_flags"] == []


def test_referral_steps_go_in_order_and_stop_at_closed():
    assert [d.next_step(s) for s in d.REFERRAL_STEPS] == ["referred", "reached_phc", "closed", None]


def test_not_checked_signs_from_the_newest_visit_are_carried_forward():
    visits = [visit(2, "2026-11-20", receipt=[row("anc_high_fever", "not_checked"), row("anc_burning_urination", "not_checked"),
                                              row("anc_convulsions", "not_checked"), row("anc_vaginal_bleeding", "ruled_out")]),
              visit(1, "2026-11-01", receipt=[row("anc_swelling_face_hands", "not_checked")])]

    assert [s["sign"] for s in d.not_asked(visits)] == ["anc_convulsions", "anc_high_fever"]


def test_review_lists_unreported_flags_and_flagged_concerns_only():
    record = {"worker_concerns": [{"quote": "she looks tired", "at": "t", "flagged": True},
                                  {"quote": "noted only", "at": "t", "flagged": False}]}
    visits = [visit(1, "2026-11-01", record, [row("bleeding", "present")])]

    before = d.patient_summary(MOTHER, visits, {}, {}, TODAY)["review"]
    after = d.patient_summary(MOTHER, visits, {}, {"flag:1:bleeding": "reported"}, TODAY)["review"]

    assert [i["key"] for i in before] == ["flag:1:bleeding", "concern:1:0"]
    assert [i["key"] for i in after] == ["concern:1:0"]


def test_disputed_signs_and_out_of_range_values_need_a_double_check():
    record = {"weight_kg": 520, "hb": 11, "bp": [300, 80], "temperature": [37, "C"]}
    visits = [visit(1, "2026-11-01", record, [row("fever", "present", disputed=True)])]

    checks = d.double_checks(MOTHER, visits, {})

    assert {c["key"] for c in checks} == {"check:1:fever", "check:1:weight_kg", "check:1:bp"}
    assert d.double_checks(MOTHER, visits, {c["key"]: "checked" for c in checks})[0]["checked"]


def test_newborn_weight_uses_the_newborn_range():
    assert d.odd_values({"weight_kg": 28}, "newborn") == [("weight_kg", 28)]
    assert d.odd_values({"weight_kg": 2.8}, "newborn") == []


def test_timeline_starts_from_the_seed_and_gives_a_neutral_direction():
    visits = [visit(2, "2026-11-20", {"weight_kg": 53.5, "bp": [110, 70]}),
              visit(1, "2026-11-01", {"weight_kg": 53.5, "bp": [120, 80]})]

    trend = d.timeline(MOTHER, visits)

    assert [p["value"] for p in trend["weight_kg"]["points"]] == [52.0, 53.5, 53.5]
    assert trend["weight_kg"]["direction"] == "same" and trend["bp"]["direction"] == "lower"
    assert "hb" not in trend


def test_dashboard_counts_tags_and_summarises_villages():
    histories = {"4127": [visit(1, "2026-11-20", {"next_visit_date": "2026-11-22"}, [row("bleeding", "present")])]}
    other = {**MOTHER, "id": "5096", "name": "Shilpa Naik", "village": "Bettahalli",
             "last_visit": {"date": "2026-09-01"}}

    view = d.dashboard([MOTHER, other], histories, {}, {}, TODAY)

    assert view["tags"] == {"due_today": 1, "overdue": 1, "danger": 1, "not_asked": 0, "needs_review": 1}
    assert view["villages"][0] == {"village": "Hosahalli", "patients": 1, "visits_this_week": 1,
                                   "visited_30_days": 1, "open_flags": 1}
    assert view["villages"][1]["visited_30_days"] == 0
    assert {p["id"] for p in view["patients"]} == {"4127", "5096"}
