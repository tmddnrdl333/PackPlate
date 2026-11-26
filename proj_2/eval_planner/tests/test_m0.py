"""The planner eval's rules on tiny hand-made data, each checked on its own."""

import csv
import json
from types import SimpleNamespace

import pytest

from app.services.filter_engine import Profile
from app.services.planner import Goal
from eval_planner import m0
from eval_planner.students import Student

RULES = {"max_protein_g": 100, "max_calories": 2000}


def dish(id, protein, calories, allergens=(), diets=(), name=None):
    return SimpleNamespace(
        id=id,
        name=name or f"dish {id}",
        course="x",
        serving_size="1 cup",
        allergens=list(allergens),
        diets=list(diets),
        unrecognized_traits=[],
        nutrition=SimpleNamespace(
            protein_g=protein, calories=calories, sodium_mg=1.0,
            ingredients="Rice, Salt", ingredient_flags={}, missing_fields=[],
        ),
    )  # fmt: skip


def student(protein=60, calories=2000, avoid=(), diets=()):
    goal = Goal(protein_g=protein, max_calories=calories,
                avoid=frozenset(avoid), diets=frozenset(diets))  # fmt: skip
    return Student(Profile(avoid=frozenset(avoid), diets=frozenset(diets)), goal)


# --- plausible labels -------------------------------------------------------


@pytest.mark.parametrize(
    "protein,calories,ok",
    [
        (30, 500, True),
        (100, 2000, True),  # both limits are inclusive
        (101, 2000, False),  # more protein than one serving has
        (50, 2001, False),  # over a whole day's calories alone
        (169, 920, False),  # Sliced Turkey, a whole 907 g roast
        (50, 199, False),  # 200 kcal of protein in 199 kcal: impossible
        (50, 200, True),
    ],
)
def test_plausible(protein, calories, ok):
    assert m0.plausible(dish(1, protein, calories), RULES) is ok


# --- one student-day --------------------------------------------------------


def test_met_when_one_location_reaches_the_goal():
    r = m0.student_day(student(60), {1: [dish(1, 30, 400), dish(2, 35, 500)]}, RULES)
    assert r["met"] and r["met_raw"]
    assert r["unsafe"] == []


def test_locations_never_mix():
    # 30 g at each of two locations: neither alone reaches 60 g.
    days = {1: [dish(1, 30, 400)], 2: [dish(2, 30, 400)]}
    r = m0.student_day(student(60), days, RULES)
    assert not r["met"] and not r["met_raw"]


def test_met_with_an_implausible_label_does_not_count():
    r = m0.student_day(student(60), {1: [dish(1, 162, 1080)]}, RULES)
    assert r["met_raw"] and not r["met"]
    assert not r["baseline"]


def test_any_usable_location_counts_even_if_another_is_implausible():
    days = {1: [dish(1, 162, 1080)], 2: [dish(2, 40, 500), dish(3, 30, 400)]}
    r = m0.student_day(student(60), days, RULES)
    assert r["met"]
    assert [loc for loc, _ in r["met_plans"]] == [2]


def test_avoided_allergen_is_never_planned():
    days = {1: [dish(1, 90, 500, allergens=["nuts"]), dish(2, 20, 300)]}
    r = m0.student_day(student(60, avoid=["nuts"]), days, RULES)
    assert not r["met"]
    assert r["unsafe"] == []


def test_untagged_dish_is_never_planned_for_a_diet():
    days = {1: [dish(1, 70, 500), dish(2, 30, 400, diets=["vegan", "vegetarian"])]}
    r = m0.student_day(student(60, diets=["vegan"]), days, RULES)
    assert not r["met"]


def test_calorie_limit_holds():
    r = m0.student_day(
        student(60, calories=800), {1: [dish(1, 30, 500), dish(2, 30, 500)]}, RULES
    )
    assert not r["met"]


def test_warned_when_every_location_falls_short():
    days = {1: [dish(1, 30, 400)], 2: [dish(2, 40, 500)]}
    r = m0.student_day(student(100), days, RULES)
    assert not r["met"] and r["warned"]


def test_not_warned_when_a_goal_is_met():
    r = m0.student_day(student(60), {1: [dish(1, 30, 400), dish(2, 35, 500)]}, RULES)
    assert r["met"] and not r["warned"]


def test_not_warned_when_only_an_implausible_plan_is_met():
    # The page shows that plan as met, so it shows no warning; the eval counts
    # the day as missed AND unwarned, so coverage can drop below 100%.
    r = m0.student_day(student(60), {1: [dish(1, 162, 1080)]}, RULES)
    assert not r["met"] and not r["warned"]


def test_not_warned_when_nothing_can_be_planned():
    # Only "none" plans: the page explains that case with its own message.
    r = m0.student_day(student(60, calories=100), {1: [dish(1, 30, 400)]}, RULES)
    assert not r["met"] and not r["warned"]


def test_baseline_needs_one_dish_alone():
    two = m0.student_day(student(60), {1: [dish(1, 30, 400), dish(2, 30, 400)]}, RULES)
    one = m0.student_day(student(60), {1: [dish(1, 65, 600)]}, RULES)
    assert two["met"] and not two["baseline"]
    assert one["met"] and one["baseline"]


def test_unsafe_dish_in_a_plan_is_reported(monkeypatch):
    # If the planner ever let an unsafe dish through, the eval must see it.
    from app.services import planner

    monkeypatch.setattr(m0, "plan", lambda items, goal: planner.Plan(
        planner.MET, list(items), 90, 500, 1))  # fmt: skip
    days = {1: [dish(1, 90, 500, allergens=["nuts"])]}
    r = m0.student_day(student(60, avoid=["nuts"]), days, RULES)
    assert r["unsafe"] == [(1, "dish 1")]


# --- small helpers ----------------------------------------------------------


@pytest.mark.parametrize(
    "goal,name",
    [(60, "60-90 g"), (90, "60-90 g"), (91, "91-120 g"), (150, "121-150 g"),
     (151, "other")],  # fmt: skip
)
def test_band(goal, name):
    assert m0.band(goal) == name


def test_rate():
    assert m0.rate(1, 3) == 0.3333
    assert m0.rate(0, 0) == 0.0


# --- the hand-check sheet ---------------------------------------------------


def pairs(n):
    return [{"student": f"avoids s{i}", "item": f"d{i}", "location_id": 1,
             "ingredients": "x", "label_key": f"k{i}"} for i in range(n)]  # fmt: skip


SETTINGS = {"hand_check": {"size": 5, "seed": 1}}


def test_draw_is_fixed_and_numbered():
    a = m0.draw(pairs(20), SETTINGS, {1: "Clark"})
    b = m0.draw(pairs(20), SETTINGS, {1: "Clark"})
    assert a == b
    assert [r["row"] for r in a] == [1, 2, 3, 4, 5]
    assert all(r["location"] == "Clark" and r["decision"] == "" for r in a)


def test_draw_takes_all_when_pool_is_small():
    assert len(m0.draw(pairs(3), SETTINGS, {})) == 3


def write_sheet(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_read_sheet_lowercases_and_allows_blank(tmp_path):
    rows = m0.draw(pairs(3), SETTINGS, {})
    rows[0]["decision"], rows[1]["decision"] = " OK ", "Missed"
    write_sheet(tmp_path / "s.csv", rows)
    got = m0.read_sheet(tmp_path / "s.csv")
    assert [r["decision"] for r in got] == ["ok", "missed", ""]


def test_read_sheet_rejects_unknown_decision(tmp_path):
    rows = m0.draw(pairs(2), SETTINGS, {})
    rows[0]["decision"] = "maybe"
    write_sheet(tmp_path / "s.csv", rows)
    with pytest.raises(m0.StaleSheet):
        m0.read_sheet(tmp_path / "s.csv")


def test_check_sheet_catches_a_changed_draw():
    expected = m0.draw(pairs(20), SETTINGS, {})
    m0.check_sheet(expected, expected)
    other = m0.draw(pairs(20), {"hand_check": {"size": 5, "seed": 2}}, {})
    with pytest.raises(m0.StaleSheet):
        m0.check_sheet(other, expected)


def test_hand_check_counts():
    rows = [{"decision": d, "student": "s", "item": "i", "note": ""}
            for d in ["ok"] * 3 + ["missed", "unclear", ""]]  # fmt: skip
    h = m0.hand_check(rows, 100, 4)
    assert (h["ok"], h["missed"], h["unclear"], h["not_checked_yet"]) == (3, 1, 1, 1)
    assert h["pairs_left_out_no_ingredients"] == 4
    assert len(h["missed_pairs"]) == 1
    assert 0.25 < h["miss_rate_upper_bound_95"] < 1


def test_hand_check_with_nothing_decided_has_no_bound():
    h = m0.hand_check([{"decision": "", "student": "s", "item": "i", "note": ""}], 1, 0)
    assert h["miss_rate_upper_bound_95"] is None


# --- the committed result ---------------------------------------------------


def test_committed_result_shape():
    r = json.loads(m0.RESULTS.read_text(encoding="utf-8"))
    assert set(r["verdicts"]) == {"useful", "safe"}
    assert r["targets"]["useful_min_rate"] == 0.9
    assert r["useful"]["student_days"] == 1200
    assert r["safe"]["unsafe_planned_dishes"] == 0
    u = r["useful"]
    assert u["missed"] == u["student_days"] - u["met"]
    assert 0 <= u["missed_with_goal_warning"] <= u["missed"]


def test_committed_sheet_matches_result():
    r = json.loads(m0.RESULTS.read_text(encoding="utf-8"))
    rows = m0.read_sheet()
    assert len(rows) == r["safe"]["hand_check"]["sampled"] == 50
