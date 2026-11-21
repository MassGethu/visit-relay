"""Wipe every saved visit and every recorded clip after judging. Prints exactly what it deleted.

    python scripts/delete_all.py          # asks first
    python scripts/delete_all.py --yes    # no question
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

from store import DEFAULT_DB  # noqa: E402


def targets() -> list[Path]:
    load_dotenv(ROOT / ".env")
    db = Path(os.getenv("DB_PATH") or DEFAULT_DB)
    found = [db.with_name(db.name + s) for s in ("", "-journal", "-wal", "-shm")]
    found.append(ROOT / "eval" / "clips")
    return [p for p in found if p.exists()]


def main() -> None:
    paths = targets()
    if not paths:
        print("Nothing to delete: no database and no eval/clips.")
        return
    print("Will permanently delete:")
    for p in paths:
        print(f"  {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}")
    if "--yes" not in sys.argv and input("Type DELETE to continue: ").strip() != "DELETE":
        print("Cancelled. Nothing deleted.")
        return
    for p in paths:
        if p.is_dir():
            n = sum(1 for f in p.rglob("*") if f.is_file())
            shutil.rmtree(p)
            print(f"Deleted folder {p.name}/ ({n} files)")
        else:
            size = p.stat().st_size
            p.unlink()
            print(f"Deleted {p.name} ({size} bytes)")
    print("Done. All saved visits and clips are gone.")


if __name__ == "__main__":
    main()
