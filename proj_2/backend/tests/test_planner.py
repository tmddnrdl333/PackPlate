"""Daily meal planner rules (Project 3, M2): pure functions, no database."""

import itertools
import math
from types import SimpleNamespace

import pytest

from app.services import filter_engine
from app.services.planner import (
    MAX_ITEMS_LIMIT,
    MET,
    NONE,
    SHORT,
    Goal,
    Plan,
    candidates,
    plan,
    rank_key,
    safety_profile,
)

_ids = itertools.count(1)


def label(protein=10.0, calories=100.0, sodium=100.0, **extra):
    values = {
        "protein_g": protein,
        "calories": calories,
        "sodium_mg": sodium,
        "serving_size": "1 each",
        "ingredients": "Chicken",
        "ingredient_flags": {},
        "missing_fields": [],
    }
    values.update(extra)
    return SimpleNamespace(**values)


def dish(
    name=None,
    protein=10.0,
    calories=100.0,
    allergens=(),
    diets=(),
    unrecognized=(),
    nutrition="default",
    serving="1 each",
):
    n = next(_ids)
    return SimpleNamespace(
        id=n,
        name=name or f"Dish {n}",
        serving_size=serving,
        allergens=list(allergens),
        diets=list(diets),
        unrecognized_traits=list(unrecognized),
        nutrition=label(protein, calories) if nutrition == "default" else nutrition,
    )


def goal(protein=50, calories=1000, **kw):
    return Goal(protein_g=protein, max_calories=calories, **kw)


def names(result: Plan) -> list[str]:
    return [i.name for i in result.items]


# --- Goal validation ---------------------------------------------------------


@pytest.mark.parametrize(
    "kw",
    [
        {"protein_g": 0, "max_calories": 100},
        {"protein_g": -5, "max_calories": 100},
        {"protein_g": 10, "max_calories": 0},
        {"protein_g": 10, "max_calories": 100, "max_items": 0},
        {"protein_g": 10, "max_calories": 100, "max_items": MAX_ITEMS_LIMIT + 1},
        {"protein_g": 10, "max_calories": 100, "avoid": frozenset({"peanuts"})},
        {"protein_g": 10, "max_calories": 100, "diets": frozenset({"keto"})},
    ],
)
def test_goal_rejects_bad_values(kw):
    with pytest.raises(ValueError):
        Goal(**kw)


def test_goal_accepts_every_known_allergen_and_diet():
    Goal(
        protein_g=1,
        max_calories=1,
        avoid=frozenset(filter_engine.ALLERGEN_KEYS),
        diets=frozenset(filter_engine.DIET_KEYS),
    )


# --- Safety: only dishes filter_engine says "fits" ----------------------------


def test_safety_profile_only_demands_usable_numbers():
    p = safety_profile(goal(avoid=frozenset({"nuts"}), diets=frozenset({"vegan"})))
    assert p.avoid == {"nuts"} and p.diets == {"vegan"}
    assert p.min_protein_g == 0 and p.max_calories == math.inf
    assert p.max_sodium_mg is None


def test_dish_with_an_avoided_allergen_is_never_planned():
    nutty = dish("Peanut Chicken", protein=60, calories=300, allergens=["nuts"])
    plain = dish("Chicken", protein=20, calories=300)
    result = plan([nutty, plain], goal(50, avoid=frozenset({"nuts"})))
    assert "Peanut Chicken" not in names(result)
    assert result.status == SHORT and names(result) == ["Chicken"]


def test_dish_not_tagged_with_required_diet_is_never_planned():
    untagged = dish(
        "Bean Bowl", protein=40
    )  # might be vegan, but not tagged: incomplete
    tagged = dish("Tofu", protein=15, diets=["vegan"])
    result = plan([untagged, tagged], goal(10, diets=frozenset({"vegan"})))
    assert names(result) == ["Tofu"]


def test_vegan_tag_satisfies_vegetarian():
    result = plan(
        [dish("Tofu", protein=15, diets=["vegan"])],
        goal(10, diets=frozenset({"vegetarian"})),
    )
    assert result.status == MET and names(result) == ["Tofu"]


def test_dish_with_unrecognized_trait_is_never_planned_when_avoiding():
    odd = dish("Mystery", protein=50, unrecognized=["Lupin"])
    result = plan([odd], goal(10, avoid=frozenset({"nuts"})))
    assert result.status == NONE


def test_ingredient_flag_doubting_a_diet_tag_blocks_the_dish():
    flagged = dish("Veggie Soup", protein=30, diets=["vegetarian"])
    flagged.nutrition.ingredient_flags = {"meat": ["chicken fat"]}
    result = plan([flagged], goal(10, diets=frozenset({"vegetarian"})))
    assert result.status == NONE


def test_dish_without_a_label_is_never_planned():
    result = plan([dish("Salad", nutrition=None)], goal(1))
    assert result.status == NONE and result.candidates == 0


@pytest.mark.parametrize("missing", ["protein_g", "calories"])
def test_dish_missing_protein_or_calories_is_never_planned(missing):
    d = dish("Half label", protein=40)
    setattr(d.nutrition, missing, None)
    assert plan([d], goal(10)).status == NONE


def test_dish_with_flagged_nutrient_is_never_planned():
    d = dish("Flagged", protein=40)
    d.nutrition.missing_fields = ["Protein"]
    assert plan([d], goal(10)).status == NONE


def test_placeholder_label_is_never_planned():
    d = dish("Bagel", protein=40)
    d.nutrition.serving_size = "Gram (1g)"
    d.nutrition.ingredients = "Flour, Water, Salt"
    assert plan([d], goal(10)).status == NONE


def test_every_planned_dish_fits_the_student():
    menu = [
        dish("A", 30, 300, allergens=["dairy"]),
        dish("B", 25, 200, diets=["vegetarian"]),
        dish("C", 25, 250, diets=["vegan"]),
        dish("D", 40, 100),
        dish("E", 20, 100, diets=["vegetarian"], nutrition=None),
    ]
    g = goal(40, avoid=frozenset({"dairy"}), diets=frozenset({"vegetarian"}))
    result = plan(menu, g)
    profile = safety_profile(g)
    assert result.items
    for item in result.items:
        assert filter_engine.check(item, profile).verdict == filter_engine.FITS


# --- The search ---------------------------------------------------------------


def test_meets_goal_under_limit():
    menu = [dish("A", 30, 400), dish("B", 30, 400), dish("C", 10, 100)]
    result = plan(menu, goal(55, 900))
    assert result.status == MET
    assert result.protein_g >= 55 and result.calories <= 900


def test_picks_fewest_calories_among_plans_that_meet_goal():
    menu = [
        dish("Steak", 50, 700),
        dish("Chicken", 30, 200),
        dish("Fish", 25, 150),
    ]
    result = plan(menu, goal(50, 1000))
    assert result.status == MET
    assert names(result) == ["Chicken", "Fish"] and result.calories == 350


def test_tie_on_calories_prefers_fewer_dishes():
    menu = [dish("Big", 40, 400), dish("Half 1", 20, 200), dish("Half 2", 20, 200)]
    result = plan(menu, goal(40, 1000))
    assert names(result) == ["Big"]


def test_never_exceeds_calorie_limit():
    menu = [dish("Heavy", 100, 1200), dish("Light", 20, 300)]
    result = plan(menu, goal(50, 1000))
    assert result.calories <= 1000 and "Heavy" not in names(result)


def test_calorie_limit_is_inclusive():
    result = plan([dish("Exact", 50, 1000)], goal(50, 1000))
    assert result.status == MET and result.calories == 1000


def test_never_exceeds_max_items():
    menu = [dish(f"Snack {i}", 10, 50) for i in range(10)]
    result = plan(menu, goal(50, 1000, max_items=3))
    assert len(result.items) == 3 and result.status == SHORT
    assert result.protein_g == 30


def test_each_dish_used_at_most_once():
    result = plan([dish("Only", 20, 100)], goal(40, 1000))
    assert names(result) == ["Only"] and result.status == SHORT


def test_same_dish_at_two_meals_counts_once():
    breakfast = dish("Scrambled Eggs", 12, 140)
    lunch = dish("Scrambled  eggs ", 12, 140)  # same dish, different spacing/case
    result = plan([breakfast, lunch], goal(20, 1000))
    assert result.candidates == 1 and result.status == SHORT
    assert names(result) == ["Scrambled Eggs"]


def test_same_name_different_serving_are_different_dishes():
    small = dish("Chicken", 15, 100, serving="3 oz")
    large = dish("Chicken", 25, 170, serving="5 oz")
    result = plan([small, large], goal(40, 1000))
    assert result.status == MET and len(result.items) == 2


def test_fractional_protein_never_overstates_the_total():
    # 3 x 16.7 = 50.1 real grams, but floored to 48: the planner can't claim 50.
    menu = [dish(f"D{i}", 16.7, 100) for i in range(3)]
    result = plan(menu, goal(50, 1000))
    assert result.status == SHORT
    assert result.protein_g == pytest.approx(50.1)


def test_met_plan_real_total_is_never_below_goal():
    menu = [dish(f"D{i}", 10.9, 90) for i in range(8)]
    result = plan(menu, goal(43.2, 1000))
    assert result.status == MET and result.protein_g >= 43.2


def test_fractional_goal_rounds_up():
    result = plan([dish("A", 50, 100)], goal(50.5, 1000))
    assert result.status == SHORT


def test_zero_protein_dishes_never_fill_a_plan():
    menu = [dish("Water", 0, 0), dish("Lettuce", 0.4, 5), dish("Chicken", 30, 200)]
    result = plan(menu, goal(20, 1000))
    assert names(result) == ["Chicken"]


def test_short_plan_maximises_protein_within_limits():
    menu = [dish("A", 20, 600), dish("B", 15, 300), dish("C", 12, 300)]
    result = plan(menu, goal(100, 700))
    assert result.status == SHORT
    assert names(result) == ["B", "C"] and result.protein_g == 27


def test_short_when_every_dish_is_over_the_limit():
    result = plan([dish("Feast", 80, 3000)], goal(50, 1000))
    assert result.status == SHORT and result.items == [] and result.candidates == 1


def test_none_when_no_dishes():
    result = plan([], goal(10))
    assert result == Plan(NONE)


def test_totals_match_the_items():
    menu = [dish("A", 21.5, 210.5), dish("B", 33.25, 300)]
    result = plan(menu, goal(50, 1000))
    assert result.protein_g == pytest.approx(54.75)
    assert result.calories == pytest.approx(510.5)


def test_items_come_back_in_input_order():
    menu = [dish("First", 10, 100), dish("Second", 30, 100), dish("Third", 20, 100)]
    result = plan(menu, goal(60, 1000))
    assert names(result) == ["First", "Second", "Third"]


def test_same_input_gives_same_plan():
    menu = [dish(f"D{i}", 5 + (i * 7) % 23, 80 + (i * 37) % 300) for i in range(40)]
    g = goal(90, 1200)
    first = plan(menu, g)
    for _ in range(3):
        assert names(plan(menu, g)) == names(first)


def test_matches_brute_force_on_small_menus():
    """The DP finds the same calories as trying every combination."""
    menu = [dish(f"D{i}", 3 + (i * 11) % 29, 60 + (i * 53) % 400) for i in range(10)]
    g = goal(70, 900, max_items=4)
    best = None
    for k in range(1, 5):
        for combo in itertools.combinations(menu, k):
            protein = sum(math.floor(d.nutrition.protein_g) for d in combo)
            cal = sum(d.nutrition.calories for d in combo)
            if protein >= 70 and cal <= 900 and (best is None or cal < best):
                best = cal
    result = plan(menu, g)
    assert best is not None and result.status == MET
    assert result.calories == best


def test_candidates_dedupes_and_keeps_order():
    a, b, a_again = dish("A"), dish("B"), dish("a")
    assert [d.name for d in candidates([a, b, a_again], goal())] == ["A", "B"]


# --- Ranking across locations ---------------------------------------------------


def test_rank_met_then_short_then_none():
    met_heavy = Plan(MET, protein_g=60, calories=900)
    met_light = Plan(MET, protein_g=60, calories=500)
    short_more = Plan(SHORT, protein_g=40, calories=900)
    short_less = Plan(SHORT, protein_g=20, calories=100)
    nothing = Plan(NONE)
    rows = [
        ("Z none", nothing),
        ("Y short less", short_less),
        ("X met heavy", met_heavy),
        ("W short more", short_more),
        ("V met light", met_light),
    ]
    ranked = sorted(rows, key=lambda r: rank_key(*r))
    assert [r[0] for r in ranked] == [
        "V met light",
        "X met heavy",
        "W short more",
        "Y short less",
        "Z none",
    ]


def test_rank_ties_break_on_name():
    rows = [("B", Plan(MET, calories=500)), ("A", Plan(MET, calories=500))]
    assert [r[0] for r in sorted(rows, key=lambda r: rank_key(*r))] == ["A", "B"]
