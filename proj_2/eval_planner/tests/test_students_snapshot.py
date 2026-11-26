"""Simulated students and the snapshot upgrade."""

import random

from eval_planner import snapshot
from eval_planner.students import load_settings, restricted_person, students
from ingestion.ingredients import matched_terms

ALWAYS_VEGAN = {
    "avoid": {"nuts": {"p": 0.0}},
    "halal": {"p": 0.0},
    "diet": {"vegan": 1.0, "vegetarian": 0.0},
}
SETTINGS = {
    "seed": 7, "students": 30, "protein_goal_g": [60, 150],
    "max_calories": [1800, 2800], "calorie_step": 100, "max_items": 6,
}  # fmt: skip


def test_every_student_has_a_restriction():
    real = load_settings()
    for s in students(real):
        assert s.profile.avoid or s.profile.diets


def test_students_are_reproducible():
    a = students(SETTINGS, ALWAYS_VEGAN)
    b = students(SETTINGS, ALWAYS_VEGAN)
    assert a == b


def test_goals_stay_in_range():
    for s in students(SETTINGS, ALWAYS_VEGAN):
        assert 60 <= s.goal.protein_g <= 150
        assert 1800 <= s.goal.max_calories <= 2800
        assert s.goal.max_calories % 100 == 0
        assert s.goal.max_items == 6
        assert s.goal.diets == s.profile.diets


def test_group_names():
    s = students(SETTINGS, ALWAYS_VEGAN)[0]
    assert s.group == "vegan"
    assert s.describe() == "is vegan"


def test_restricted_person_redraws_until_restricted():
    p = restricted_person(random.Random(1), ALWAYS_VEGAN)
    assert p.diets == frozenset({"vegan"})


def test_upgrade_rebuilds_flags_like_production():
    old = {"labels": {"k": {"ingredients": "Milk, Peanuts", "calories": 1}}}
    new = snapshot.upgrade(old)
    label = new["labels"]["k"]
    assert label["ingredient_flags"] == matched_terms("Milk, Peanuts")
    assert label["missing_fields"] == [] and label["serving_size"] is None
    assert new["reviews"] == []
    assert "ingredient_flags" not in old["labels"]["k"]  # input untouched


def test_upgrade_keeps_existing_fields():
    s = {"labels": {"k": {"ingredients": "Milk", "ingredient_flags": {},
                          "missing_fields": ["Protein"], "serving_size": "1 cup"}},
         "reviews": [1]}  # fmt: skip
    new = snapshot.upgrade(s)
    assert new["labels"]["k"]["ingredient_flags"] == {}
    assert new["labels"]["k"]["missing_fields"] == ["Protein"]
    assert new["reviews"] == [1]


def test_campus_days_cover_both_snapshots():
    days, names, raw = snapshot.campus_days(snapshot.load())
    assert list(days) == ["2026-10-12", "2026-10-13", "2026-10-14",
                          "2026-10-20", "2026-10-21", "2026-10-22"]  # fmt: skip
    assert len(names) == 24
    first_day = days["2026-10-12"]
    loc, items = next(iter(first_day.items()))
    assert items and (("2026-10-12", loc, items[0].id) in raw)
