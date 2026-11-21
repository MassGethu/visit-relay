"""Plays the PLAN.md demo visit as text, with synthetic transcripts. No API keys needed.

    python tools/demo_visit.py
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from asha.visit import Visit  # noqa: E402

TURNS = [
    "ANC visit hai, wajan baavan kilo, BP ek sau bees by assi",
    "aur thoda khoon aa raha tha kal, ab nahi",
    "agla visit 20 november ko aana hai",
]


def main() -> None:
    v = Visit("anc", subject="mother", lang="hi", today=dt.date(2026, 11, 13), use_llm=False,
              use_store=False)
    show = lambda who, lines: [print(f"{who:>6}: {line}") for line in lines]
    show("agent", v.start())
    for t in TURNS:
        show("ASHA", [t])
        show("agent", v.hear(t))
    show("agent", v.readback())
    show("ASHA", ["haan, fits nahi, sir dard nahi, bukhaar nahi. record pakka"])
    show("agent", v.hear("fits nahi aaye, sir dard nahi hai, bukhaar nahi hai"))
    show("agent", v.hear("record pakka"))
    print("\nBrowser events (types):", [e["type"] for e in v.events()])
    print("\nDanger-sign receipt (non-empty rows):")
    for r in v.danger.receipt():
        if r["status"] != "not_checked":
            extra = " (history)" if r["history"] else ""
            print(f"  {r['status']:<10} {r['sign']:<36} \"{r['quote']}\"{extra}  [{r['source']}]")
    unchecked = sum(r["status"] == "not_checked" for r in v.danger.receipt())
    print(f"  not_checked: {unchecked} signs (shown to the ANM as 'not asked', never as 'no')")
    print("\nRecord:", v.record)


if __name__ == "__main__":
    main()
