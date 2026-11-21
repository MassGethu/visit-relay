"""Worker concerns: her worry outside the checklist, kept verbatim, flagged for ANM on request.
A concern never changes a checklist state, and never delays a danger alert."""
import datetime as dt

import pytest
from cryptography.fernet import Fernet

from asha.concern import carries_content, is_flag_request, is_worry, words_of
from asha.guard import guard
from asha.speak import TEMPLATES
from asha.visit import Visit
from store import Store

TODAY = dt.date(2026, 11, 13)
CONCERN = "mujhe chinta hai, saas usko khana kam deti hai"
DANGER = "thoda khoon aa raha hai"


def make(**kw) -> Visit:
    kw.setdefault("use_llm", False)
    kw.setdefault("use_store", False)
    v = Visit("anc", subject="mother", lang="hi", today=TODAY, **kw)
    v.start()
    v.events()
    return v


def last_record(events):
    return [e for e in events if e["type"] == "record"][-1]["fields"]


def statuses(v):
    return {r["sign"]: r["status"] for r in v.danger.receipt()}


# ---------- detection ----------

@pytest.mark.parametrize("said", ["ANM ko batao", "एएनएम को बताइए", "ANM ko bata do", "flag karo",
                                  "ANM ಗೆ ತಿಳಿಸಿ", "tell ANM"])
def test_flag_requests_are_recognised(said):
    assert is_flag_request(words_of(said))


@pytest.mark.parametrize("said", ["ANM ko bata diya", "ANM aayi thi", "wajan baavan kilo"])
def test_past_tense_or_unrelated_is_not_a_flag(said):
    assert not is_flag_request(words_of(said))


def test_flag_with_its_own_words_carries_content():
    assert not carries_content(words_of("ANM ko batao"))
    assert carries_content(words_of("ANM ko batao ki saas khana nahi deti"))


@pytest.mark.parametrize("said", [CONCERN, "मुझे चिंता है", "kuch theek nahi lag raha", "I am worried"])
def test_worry_words(said):
    assert is_worry(words_of(said))


# ---------- visit 1: concern outside the checklist ----------

def test_concern_outside_checklist_is_kept_verbatim_and_changes_no_state():
    v = make()
    before = statuses(v)
    lines = v.hear(CONCERN)
    ev = v.events()
    assert "alert" not in [e["type"] for e in ev]
    assert last_record(ev)["worker_concerns"] == [
        {"quote": CONCERN, "at": last_record(ev)["worker_concerns"][0]["at"], "flagged": False}]
    assert lines == [TEMPLATES["concern_noted"]["hi"]]
    assert statuses(v) == before                         # every sign still not_checked
    assert set(before.values()) == {"not_checked"}


def test_short_flag_request_flags_the_last_concern():
    v = make()
    v.hear(CONCERN)
    lines = v.hear("ANM ko batao")
    concerns = last_record(v.events())["worker_concerns"]
    assert lines == [TEMPLATES["concern_flagged"]["hi"]]
    assert [c["flagged"] for c in concerns] == [True]
    assert concerns[0]["quote"] == CONCERN               # the flag request itself is not a concern


def test_flag_request_with_content_is_saved_already_flagged():
    v = make()
    said = "ANM ko batao ki saas usko bahar nahi jaane deti"
    assert v.hear(said) == [TEMPLATES["concern_flagged"]["hi"]]
    assert last_record(v.events())["worker_concerns"][0] == {
        "quote": said, "at": v.record["worker_concerns"][0]["at"], "flagged": True}


def test_flag_with_nothing_to_flag_asks_her():
    v = make()
    assert v.hear("ANM ko batao") == [TEMPLATES["concern_missing"]["hi"]]
    assert "worker_concerns" not in v.record


# ---------- visit 2: concern plus a checklist danger sign ----------

def test_danger_alert_comes_first_with_its_citation_when_a_concern_is_also_said():
    v = make()
    lines = v.hear(f"{CONCERN}, aur {DANGER}")
    ev = v.events()
    alerts = [e for e in ev if e["type"] == "alert"]
    assert len(alerts) == 1 and alerts[0]["source"] and alerts[0]["page"]
    assert "PHC" in lines[0]                              # spoken alert first, same turn
    assert lines[1] == TEMPLATES["concern_noted"]["hi"]
    assert ev.index(alerts[0]) < [i for i, e in enumerate(ev) if e["type"] == "record"][-1]
    assert list(statuses(v).values()).count("present") == 1
    assert v.record["worker_concerns"][0]["quote"] == f"{CONCERN}, aur {DANGER}"


def test_flagging_a_concern_does_not_touch_the_danger_receipt():
    v = make()
    v.hear(DANGER)
    v.hear(CONCERN)
    before = statuses(v)
    v.hear("ANM ko batao")
    assert statuses(v) == before
    assert list(before.values()).count("present") == 1


# ---------- speech and storage ----------

@pytest.mark.parametrize("name", ["concern_noted", "concern_flagged", "concern_missing"])
@pytest.mark.parametrize("lang", ["hi", "kn", "en"])
def test_concern_templates_pass_the_guard(name, lang):
    text = TEMPLATES[name][lang]
    assert guard(text) == (text, [])


def test_concerns_are_saved_encrypted_with_audit_rows(tmp_path):
    store = Store(tmp_path / "v.db", Fernet.generate_key())
    v = make(store=store)
    v.hear(CONCERN)
    v.hear("ANM ko batao")
    v.hear("record pakka")
    kinds = [(a["kind"], a["by"], a["quote"]) for a in store.audit(v.visit_id)]
    assert ("concern_flagged", "asha", CONCERN) in kinds
    assert store.load_visit(v.visit_id)["record"]["worker_concerns"][0]["flagged"] is True
    assert "saas".encode() not in (tmp_path / "v.db").read_bytes()
