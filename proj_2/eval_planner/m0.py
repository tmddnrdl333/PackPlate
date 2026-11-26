"""Project 3 M0: does the daily meal planner work for students with restrictions?

One command, from proj_2/:

    python -m eval_planner.m0            # compute, print, write eval_planner/results.json
    python -m eval_planner.m0 --check    # recompute; fail if it differs from results.json

Plan and targets: docs/p3-m0-planner-eval.md. In short, for simulated students
with at least one restriction, on six frozen campus days:

Useful   on >= 90% of student-days, some location's plan from
         app.services.planner.plan() (the function the API uses) is `met`
         (protein >= goal, calories <= limit) AND every planned dish has a
         plausible label (see settings.json). A plan built on a whole-pan label
         isn't one a student can eat, so it doesn't count.
Safe     (a) automatic: 0 planned dishes that filter_engine.check() doesn't call
         `fits` for that student's full profile; (b) by hand: 0 missed in 50
         random planned (dish, student) pairs whose ingredients a person read.
Baseline the single best dish (what PackPlate offered before the planner): some
         safe, plausible dish alone reaches the goal under the limit.
Warning  (descope decision, after the first result) of the missed student-days,
         how many get the planner page's "no location can reach your goal"
         warning: no location's plan is `met` and at least one is `short`.

A missed target is reported, not an error. Only a crash, a stale hand-check
sheet, or (with --check) a changed result fails.
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from app.services import filter_engine
from app.services.planner import MET, SHORT, candidates, plan
from eval_loop2.m0 import upper_bound
from eval_planner.snapshot import campus_days, load
from eval_planner.students import Student, load_settings, students

RESULTS = Path(__file__).parent / "results.json"
SHEET = Path(__file__).parent / "data" / "sample.csv"
DECISIONS = {"ok", "missed", "unclear"}
GOAL_BANDS = ((60, 90), (91, 120), (121, 150))


class StaleSheet(Exception):
    """The hand-check sheet doesn't match what the snapshots and the draw produce."""


def plausible(item, rules: dict) -> bool:
    """Could one serving really have this label? (See settings.json.)"""
    n = item.nutrition
    return (
        n.protein_g <= rules["max_protein_g"]
        and n.calories <= rules["max_calories"]
        and n.protein_g * 4 <= n.calories
    )


def student_day(student: Student, locations: dict, rules: dict) -> dict:
    """One student on one day: every location's plan, scored."""
    full = filter_engine.Profile(avoid=student.profile.avoid,
                                 diets=student.profile.diets)  # fmt: skip
    goal = student.goal
    met_raw = met_usable = baseline = short = False
    unsafe, met_plans = [], []
    for loc, items in locations.items():
        result = plan(items, goal)
        for dish in result.items:
            if filter_engine.check(dish, full).verdict != filter_engine.FITS:
                unsafe.append((loc, dish.name))
        short = short or result.status == SHORT
        if result.status == MET:
            met_raw = True
            if all(plausible(d, rules) for d in result.items):
                met_usable = True
                met_plans.append((loc, result.items))
        if not baseline:
            baseline = any(
                plausible(d, rules)
                and d.nutrition.protein_g >= goal.protein_g
                and d.nutrition.calories <= goal.max_calories
                for d in candidates(items, goal)
            )
    # The planner page's goal warning (frontend/src/lib/planner.ts, goalWarning):
    # shown when no location's plan is `met` and at least one is `short`.
    warned = not met_raw and short
    return {"met_raw": met_raw, "met": met_usable, "baseline": baseline,
            "warned": warned, "unsafe": unsafe,
            "met_plans": met_plans}  # fmt: skip


def rate(hits: int, total: int) -> float:
    """hits / total, rounded to 4 places (0 when there's nothing to count)."""
    return round(hits / total, 4) if total else 0.0


def band(goal_g: float) -> str:
    """The goal band a protein goal falls in, e.g. "91-120 g"."""
    for lo, hi in GOAL_BANDS:
        if lo <= goal_g <= hi:
            return f"{lo}-{hi} g"
    return "other"


def run(settings: dict, days: dict, raw: dict):
    """Score every student-day. Returns the Useful numbers and the hand-check pool."""
    rules = settings["plausible_label"]
    totals = Counter()
    by = defaultdict(Counter)  # (kind, key) -> Counter(n, met)
    unsafe, pool, no_ingredients = [], {}, set()
    for student in students(settings):
        for day, locations in days.items():
            r = student_day(student, locations, rules)
            totals["n"] += 1
            for k in ("met", "met_raw", "baseline"):
                totals[k] += r[k]
            if not r["met"]:
                totals["missed"] += 1
                totals["missed_warned"] += r["warned"]
            for kind, key in (("group", student.group),
                              ("goal", band(student.goal.protein_g)),
                              ("day", day)):  # fmt: skip
                by[(kind, key)]["n"] += 1
                by[(kind, key)]["met"] += r["met"]
                by[(kind, key)]["baseline"] += r["baseline"]
            unsafe += [
                (day, loc, name, student.describe()) for loc, name in r["unsafe"]
            ]
            for loc, items in r["met_plans"]:
                for d in items:
                    info = raw[(day, loc, d.id)]
                    pair = (info["label_key"], student.describe())
                    if not info["ingredients"].strip():
                        no_ingredients.add(pair)
                        continue
                    pool.setdefault(pair, {
                        "student": student.describe(), "item": d.name,
                        "location_id": loc, "ingredients": info["ingredients"],
                        "label_key": info["label_key"],
                    })  # fmt: skip
    n = totals["n"]
    useful = {
        "student_days": n,
        "students": settings["students"],
        "days": list(days),
        "met": totals["met"],
        "met_rate": rate(totals["met"], n),
        "met_rate_counting_implausible_labels": rate(totals["met_raw"], n),
        "baseline_single_dish_rate": rate(totals["baseline"], n),
        "missed": totals["missed"],
        "missed_with_goal_warning": totals["missed_warned"],
        "goal_warning_coverage": rate(totals["missed_warned"], totals["missed"]),
        "by_group": {}, "by_goal": {}, "by_day": {},
    }  # fmt: skip
    order = [f"{lo}-{hi} g" for lo, hi in GOAL_BANDS]  # bands low to high

    def sort_key(entry):
        (kind, key), _ = entry
        return (kind, order.index(key) if key in order else 0, key)

    for (kind, key), c in sorted(by.items(), key=sort_key):
        useful[f"by_{kind}"][key] = {
            "student_days": c["n"],
            "met_rate": rate(c["met"], c["n"]),
            "baseline_rate": rate(c["baseline"], c["n"]),
        }
    pairs = [pool[k] for k in sorted(pool)]
    return useful, unsafe, pairs, len(no_ingredients)


def draw(pairs: list[dict], settings: dict, names: dict) -> list[dict]:
    """The fixed random sample for the hand check, numbered from 1."""
    hc = settings["hand_check"]
    picked = random.Random(hc["seed"]).sample(pairs, min(hc["size"], len(pairs)))
    picked.sort(key=lambda p: (p["student"], p["item"]))
    return [
        {"row": i, "student": p["student"], "item": p["item"],
         "location": names.get(p["location_id"], str(p["location_id"])),
         "ingredients": p["ingredients"], "decision": "", "note": "",
         "label_key": p["label_key"]}
        for i, p in enumerate(picked, 1)
    ]  # fmt: skip


def read_sheet(path: Path = SHEET) -> list[dict]:
    """The sheet, decisions lowercased. A blank decision means not checked yet."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["decision"] = (r["decision"] or "").strip().lower()
        if r["decision"] and r["decision"] not in DECISIONS:
            raise StaleSheet(
                f"row {r['row']}: decision {r['decision']!r} must be blank or one "
                f"of {sorted(DECISIONS)}"
            )
    return rows


def check_sheet(filled: list[dict], expected: list[dict]):
    """The sheet must hold exactly the pairs the fixed draw gives, in order."""

    def key(r):
        return (str(r["row"]), r["label_key"], r["student"])

    if [key(r) for r in filled] != [key(r) for r in expected]:
        raise StaleSheet(
            "the hand-check sheet doesn't match the snapshots and the draw any more; "
            "its decisions may belong to different dishes"
        )


def hand_check(rows: list[dict], pool_size: int, left_out: int) -> dict:
    """The Safe numbers from the hand check (blank decisions count as not checked)."""
    counts = Counter(r["decision"] for r in rows)
    decided = counts["ok"] + counts["missed"]
    return {
        "pairs_in_pool": pool_size,
        "pairs_left_out_no_ingredients": left_out,
        "sampled": len(rows),
        "not_checked_yet": counts[""],
        "ok": counts["ok"],
        "missed": counts["missed"],
        "unclear": counts["unclear"],
        "miss_rate_upper_bound_95": upper_bound(counts["missed"], decided)
        if decided else None,
        "missed_pairs": [
            {"student": r["student"], "item": r["item"], "note": r["note"]}
            for r in rows if r["decision"] == "missed"
        ],  # fmt: skip
    }


def evaluate() -> dict:
    """Run the whole eval on the committed inputs and return the result."""
    settings = load_settings()
    days, names, raw = campus_days(load())
    useful, unsafe, pairs, left_out = run(settings, days, raw)
    filled = read_sheet()
    check_sheet(filled, draw(pairs, settings, names))
    hand = hand_check(filled, len(pairs), left_out)
    t = settings["targets"]
    if hand["not_checked_yet"]:
        hand_verdict = "PENDING"
    else:
        hand_verdict = "MET" if hand["missed"] <= t["safe_max_missed"] else "MISSED"
    auto_ok = len(unsafe) <= t["safe_max_unsafe_auto"]
    if not auto_ok or hand_verdict == "MISSED":
        safe_verdict = "MISSED"
    else:
        safe_verdict = hand_verdict
    return {
        "claim": "For simulated students with at least one dietary restriction, "
        "the planner finds a plan at one location that meets their daily protein "
        "goal under their calorie limit, using only dishes PackPlate marks safe "
        "and labels one serving can have, on at least 90% of student-days.",
        "useful": useful,
        "safe": {
            "unsafe_planned_dishes": len(unsafe),
            "unsafe_examples": [list(u) for u in unsafe[:10]],
            "hand_check": hand,
        },
        "targets": t,
        "verdicts": {
            "useful": "MET" if useful["met_rate"] >= t["useful_min_rate"] else "MISSED",
            "safe": safe_verdict,
        },
    }


def show(result: dict) -> str:
    """The result as the table printed on the terminal."""
    u, s, v = result["useful"], result["safe"], result["verdicts"]
    h = s["hand_check"]
    lines = [
        f"P3 M0 planner eval: {u['students']} restricted students x "
        f"{len(u['days'])} days ({u['days'][0]}..{u['days'][-1]}) = "
        f"{u['student_days']} student-days",
        "",
        f"{'':34}{'Planner':>9}{'1 dish':>9}{'n':>7}",
        f"{'All restricted students':34}{u['met_rate']:>9.1%}"
        f"{u['baseline_single_dish_rate']:>9.1%}{u['student_days']:>7}",
    ]
    for kind in ("group", "goal", "day"):
        for key, c in u[f"by_{kind}"].items():
            lines.append(f"  {kind} {key:28}{c['met_rate']:>9.1%}"
                         f"{c['baseline_rate']:>9.1%}{c['student_days']:>7}")  # fmt: skip
    lines += [
        "",
        f"Counting plans built on implausible labels: "
        f"{u['met_rate_counting_implausible_labels']:.1%}",
        f"Missed student-days where the page warns the goal is out of reach: "
        f"{u['missed_with_goal_warning']} of {u['missed']} "
        f"({u['goal_warning_coverage']:.1%})",
        f"Unsafe planned dishes (automatic check): {s['unsafe_planned_dishes']}",
        f"Hand check: {h['sampled']} sampled of {h['pairs_in_pool']} planned pairs: "
        f"{h['ok']} ok, {h['missed']} missed, {h['unclear']} unclear, "
        f"{h['not_checked_yet']} not checked yet",
        "",
        f"Useful (>= {result['targets']['useful_min_rate']:.0%} of student-days): "
        f"{v['useful']}",
        f"Safe   (0 unsafe, 0 missed by hand):       {v['safe']}",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    """Run the eval; with --check, compare with results.json instead of writing it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="fail if the result differs from results.json")  # fmt: skip
    args = parser.parse_args(argv)
    try:
        result = evaluate()
    except StaleSheet as e:
        print(f"stale hand-check sheet: {e}", file=sys.stderr)
        return 2
    print(show(result))
    text = json.dumps(result, indent=1, ensure_ascii=False) + "\n"
    if args.check:
        if not RESULTS.exists() or RESULTS.read_text(encoding="utf-8") != text:
            print("\nresult differs from eval_planner/results.json", file=sys.stderr)
            return 1
        print("\nmatches eval_planner/results.json")
        return 0
    RESULTS.write_text(text, encoding="utf-8")
    print("\nwrote eval_planner/results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
