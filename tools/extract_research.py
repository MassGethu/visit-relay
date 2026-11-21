"""Copy the cited data out of research/*.md into backend/data/.

The research files are the single source of truth. Re-run this after the
research is updated:  python tools/extract_research.py

Outputs
  danger_signs.json  73 signs with official wording, source and page (01, Topic 1)
  lexicon.json       spoken phrases per sign, hi / kn / codemix / negations (01, Topic 2)
  inverted.txt       signs whose danger phrase itself contains a negator
  glossary.csv       199 ASHA field terms with spoken forms and ASR variants (02, Topic 3)
  numbers.tsv        0-100 in Hindi and Kannada, script and roman (02, 4c)

The research YAML is not strictly valid YAML (a quoted string is often
followed by more text), so it is read line by line here. Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
OUT = ROOT / "backend" / "data"

# research/01 "Risks" item 2 names these as expressed with a negator, in
# addition to the ones marked with a warning sign in the lexicon itself.
RISKS_INVERTED = {
    "anc_reduced_fetal_movement", "nb_poor_feeding", "nb_no_urine_stool",
    "pnc_no_urine", "ch_unable_to_drink", "nb_weak_cry", "nb_birth_asphyxia",
    "anc_retained_placenta", "ch_fever_persistent", "ch_lethargic_unconscious",
}


def fenced_blocks(text: str, lang: str) -> list[str]:
    return re.findall(rf"```{lang}\n(.*?)```", text, flags=re.S)


def _scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"' and raw.count('"') == 2:
        return raw[1:-1]
    return raw


def parse_signs(block: str) -> list[dict]:
    signs: list[dict] = []
    for line in block.splitlines():
        m = re.match(r"^  - id:\s*(\S+)", line)
        if m:
            signs.append({"id": m.group(1)})
            continue
        m = re.match(r"^    ([a-z_]+):\s*(.*)$", line)
        if m and signs:
            signs[-1][m.group(1)] = _scalar(m.group(2))
    return signs


def parse_lexicon(block: str) -> dict:
    """{sign: {lang: [{"script", "roman", "provenance"}], "notes": [...]}}"""
    lex: dict = {}
    sign = lang = None
    for line in block.splitlines():
        if m := re.match(r"^  ([a-z0-9_]+):", line):
            sign, lang = m.group(1), None
            lex[sign] = {}
        elif m := re.match(r"^    ([a-z]+):", line):
            lang = m.group(1)
            lex[sign][lang] = []
        elif (m := re.match(r'^      - "(.*)"\s*(#.*)?$', line)) and sign and lang:
            text = m.group(1)
            if text.startswith("NOTE:"):
                lex[sign].setdefault("notes", []).append(text[5:].strip())
                continue
            parts = [p.strip() for p in text.split(" | ")]
            if lang != "negations" and len(parts) >= 2 and parts[-1].startswith(("OFFICIAL", "UNSOURCED")):
                provenance = parts.pop()
            else:
                provenance = "UNSOURCED-linguistic"
            entry = {"script": parts[0], "roman": parts[1] if len(parts) > 1 else parts[0],
                     "provenance": provenance}
            lex[sign][lang].append(entry)
    return lex


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    danger_md = (RESEARCH / "01-danger-signs.md").read_text(encoding="utf-8")
    vocab_md = (RESEARCH / "02-vocab-numbers.md").read_text(encoding="utf-8")

    yaml_blocks = fenced_blocks(danger_md, "yaml")
    signs = next(b for b in yaml_blocks if b.lstrip().startswith("danger_signs:"))
    lexicon = next(b for b in yaml_blocks if b.lstrip().startswith("lexicon:"))
    dump = lambda name, obj: (OUT / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    dump("danger_signs.json", parse_signs(signs))
    dump("lexicon.json", parse_lexicon(lexicon))

    marked = set(re.findall(r"^  ([a-z0-9_]+):\s*#\s*⚠", lexicon, flags=re.M))
    inverted = sorted(marked | RISKS_INVERTED)
    (OUT / "inverted.txt").write_text("\n".join(inverted) + "\n", encoding="utf-8")

    csv_block = fenced_blocks(vocab_md, "csv")[0]
    (OUT / "glossary.csv").write_text(csv_block, encoding="utf-8")

    rows = []
    for line in vocab_md.splitlines():
        m = re.match(r"^\| (\d{1,3}) \| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\|", line)
        if m:
            n, hi_s, hi_r, kn_s, kn_r = (x.strip() for x in m.groups())
            rows.append("\t".join([n, hi_s, hi_r, kn_s, kn_r]))
    if len(rows) != 101:
        print(f"expected 101 number rows, found {len(rows)}", file=sys.stderr)
        return 1
    (OUT / "numbers.tsv").write_text(
        "n\thi_script\thi_roman\tkn_script\tkn_roman\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT}: inverted={len(inverted)} numbers={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
