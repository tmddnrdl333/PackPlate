"""Write the hand-check sheet: 50 random (dish, student) pairs from planned meals.

Run once, from proj_2/:

    python -m eval_planner.sample

It writes eval_planner/data/sample.csv and refuses to overwrite it once it
exists. A person fills in `decision` for each row after reading the dish's full
ingredient list against the student's restrictions, without looking at
PackPlate's icons or flags: "ok", "missed" (the ingredients name something
the student must avoid), or "unclear" (the label can't tell).
"""

import csv
import sys

from eval_planner.m0 import SHEET, draw, run
from eval_planner.snapshot import campus_days, load
from eval_planner.students import load_settings

COLUMNS = ["row", "student", "item", "location", "ingredients", "decision", "note",
           "label_key"]  # fmt: skip


def main() -> int:
    """Draw the sheet once; never overwrite one that may hold decisions."""
    if SHEET.exists():
        print(f"{SHEET} exists; delete it first to redraw", file=sys.stderr)
        return 1
    settings = load_settings()
    days, names, raw = campus_days(load())
    _, _, pairs, _ = run(settings, days, raw)
    rows = draw(pairs, settings, names)
    SHEET.parent.mkdir(exist_ok=True)
    with SHEET.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {SHEET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
