"""The six frozen campus days the planner eval runs on, as today's API sees them.

Both of the original team's snapshots are used: Oct 12-14 (eval/data) and
Oct 20-22 (eval_loop2/data). They are read, never changed.

The Oct 12-14 snapshot was exported before PackPlate scanned ingredient lists,
so its labels have no `ingredient_flags`. Production computes that field as
`ingestion.ingredients.matched_terms(ingredients)` (ingestion/normalize.py), so
the same call here gives exactly what the live filter would read. It also has
no `missing_fields`, `serving_size`, or approved label reviews; those are left
empty (NC State's incomplete-nutrient flags are unknown for those three days).
"""

import copy
import json
from collections import defaultdict
from pathlib import Path

from eval_loop2.snapshot import approved_reviews, packplate_item
from ingestion.ingredients import matched_terms

PROJ = Path(__file__).resolve().parent.parent
SNAPSHOTS = (
    PROJ / "eval" / "data" / "snapshot.json",
    PROJ / "eval_loop2" / "data" / "snapshot.json",
)


def upgrade(snapshot: dict) -> dict:
    """A copy with every field today's filter reads, filling what an old export lacks."""
    s = copy.deepcopy(snapshot)
    s.setdefault("reviews", [])
    for label in s["labels"].values():
        if "ingredient_flags" not in label:
            label["ingredient_flags"] = matched_terms(label.get("ingredients"))
        label.setdefault("missing_fields", [])
        label.setdefault("serving_size", None)
    return s


def load(paths=SNAPSHOTS) -> list[dict]:
    """Every snapshot, upgraded."""
    return [upgrade(json.loads(Path(p).read_text(encoding="utf-8"))) for p in paths]


def campus_days(snapshots: list[dict]) -> tuple[dict, dict, dict]:
    """Every campus day, as (days, names, raw).

    days:  {date: {location_id: [items as the API hands them to the planner]}};
           all of a location's menus that day are pooled, as the API does
           without `meals`.
    names: {location_id: location name}.
    raw:   {(date, location_id, item id): {"ingredients", "label_key"}}, for
           the hand-check sheet.
    """
    days: dict = defaultdict(lambda: defaultdict(list))
    names: dict[int, str] = {}
    raw: dict = {}
    for s in snapshots:
        approved = approved_reviews(s)
        names.update({loc["id"]: loc["name"] for loc in s["locations"]})
        for menu in s["menus"]:
            loc = menu["location_id"]
            for item in menu["items"]:
                view = packplate_item(item, loc, s, approved)
                days[menu["date"]][loc].append(view)
                label = s["labels"][item["label"]] if item["label"] else None
                raw[(menu["date"], loc, item["id"])] = {
                    "ingredients": (label or {}).get("ingredients") or "",
                    "label_key": item["label"] or "",
                }
    ordered = {d: dict(sorted(days[d].items())) for d in sorted(days)}
    return ordered, names, raw
