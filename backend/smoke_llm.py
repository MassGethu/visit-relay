"""Smoke test for the LLM layer: runs understand() on 3 sentences and prints JSON + timing.

    .venv/bin/python backend/smoke_llm.py            # Groq first, then Ollama
    .venv/bin/python backend/smoke_llm.py --only ollama

Done when sentence 2 returns anc_vaginal_bleeding, sentence 3 the newborn signs, each call < ~1.5 s.
"""
import argparse
import json
import logging
import sys
import time

import llm

CASES = [
    ("anc", "ANC visit hai, wajan baavan kilo, BP ek sau bees by assi, IFA goli roz le rahi hai"),
    ("anc", "thoda khoon aa raha tha kal, ab nahi"),
    ("hbnc", "baby bilkul dheela pad gaya hai aur doodh nahi pee raha"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=llm.PROVIDERS, help="test a single provider")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    if args.only:
        llm.PROVIDERS = (args.only,)

    failed = 0
    for visit_type, sentence in CASES:
        t0 = time.perf_counter()
        out = llm.understand(sentence, visit_type, {})
        total = round((time.perf_counter() - t0) * 1000)
        print(f"\n[{visit_type}] {sentence}\n  total {total} ms")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        failed += not out["ok"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
