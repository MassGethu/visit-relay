"""Print median and p90 voice pipeline timings from the event CSV."""
from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


STEPS = (
    ("Release → commit*", "release", "commit_sent"),
    ("Commit → transcript", "commit_sent", "transcript"),
    ("Transcript → rules", "transcript", "rules_done"),
    ("Transcript → LLM", "transcript", "llm_done"),
    ("Rules → first TTS byte", "rules_done", "first_tts_byte"),
    ("LLM → first TTS byte", "llm_done", "first_tts_byte"),
    ("First TTS byte → playback*", "first_tts_byte", "first_audio_played"),
    ("Release → first playback", "release", "first_audio_played"),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(__file__).resolve().parents[1] / "eval" / "latency.csv"
    parser.add_argument("csv_path", type=Path, nargs="?", default=default)
    args = parser.parse_args()
    turns = defaultdict(dict)
    try:
        with args.csv_path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                stages = turns[row["session"], row["turn"]]
                stage, time = row["stage"], float(row["timestamp_ms"])
                stages[stage] = min(time, stages.get(stage, time))
    except (OSError, KeyError, ValueError) as exc:
        parser.exit(1, f"Cannot read latency data: {exc}\n")
    print(f"{'Step':<32} {'n':>5} {'median ms':>12} {'p90 ms':>10}")
    for label, start, end in STEPS:
        values = sorted(stages[end] - stages[start] for stages in turns.values()
                        if start in stages and end in stages)
        if values:
            p90 = values[math.ceil(len(values) * 0.9) - 1]
            print(f"{label:<32} {len(values):>5} {statistics.median(values):>12.1f} {p90:>10.1f}")
        else:
            print(f"{label:<32} {0:>5} {'—':>12} {'—':>10}")
    print("* Cross-device steps depend on the phone and server clock alignment.")
    print("Negative values can occur when a VAD transcript or alert precedes release or LLM completion.")


if __name__ == "__main__":
    main()
