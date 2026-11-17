"""Meal planner route (Project 3, M2) against the test database."""

from datetime import UTC, date, datetime

import pytest

from app.services.label_reviews import dish_name, ingredients_hash
from db.models import LabelReview

TUE = date(2026, 10, 6)
WED = date(2026, 10, 7)


@pytest.fixture
def campus(seed):
    """Two locations on Tuesday.

    On the Oval (6): two stations, breakfast and lunch, nut-free protein spread out.
    Clark (2): one big high-protein dish that contains nuts.
    """
    seed.location(6, "On the Oval", "on-the-oval")
    seed.location(2, "Clark Dining Hall", "clark")
    seed.menu(61, 6, TUE, "Breakfast")
    seed.menu(62, 6, TUE, "Lunch")
    seed.menu(21, 2, TUE, "Lunch")

    seed.nutrition("6|eggs|1 each", location_id=6, protein_g=13, calories=140)
    seed.nutrition("6|chicken|1 each", location_id=6, protein_g=30, calories=250)
    seed.nutrition("6|tofu|1 each", location_id=6, protein_g=18, calories=200)
    seed.nutrition("6|pizza|1 each", location_id=6, protein_g=12, calories=290)
    seed.nutrition(
        "2|satay|1 each",
        location_id=2,
        protein_g=60,
        calories=400,
        contains=["Contains Nuts"],
    )

    seed.item(
        61, "Scrambled Eggs", "6|eggs|1 each", allergens=["egg"], diets=["vegetarian"]
    )
    seed.item(62, "Grilled Chicken", "6|chicken|1 each", course="Flashpoint - Entree")
    seed.item(
        62,
        "Tofu Bowl",
        "6|tofu|1 each",
        allergens=["soy"],
        diets=["vegan"],
        course="Fahrenheit - Homestyle Entree",
    )
    seed.item(
        62,
        "Cheese Pizza",
        "6|pizza|1 each",
        allergens=["dairy", "gluten"],
        diets=["vegetarian"],
        course="Fahrenheit - Pizza",
    )
    seed.item(62, "Mystery Salad", diets=["vegan"])  # no label: never planned
    seed.item(21, "Chicken Satay", "2|satay|1 each", allergens=["nuts"])


def post(client, body, **params):
    params.setdefault("date", "2026-10-06")
    return client.post("/planner/day", params=params, json=body)


def by_location(response):
    return {p["location_name"]: p for p in response.json()}


def test_plan_mixes_stations_within_one_location(client, campus):
    response = post(client, {"protein_goal_g": 60, "max_calories": 1000})
    assert response.status_code == 200
    oval = by_location(response)["On the Oval"]
    assert oval["status"] == "met"
    stations = {i["course"] for i in oval["items"]}
    assert len(stations) >= 2  # Flashpoint and Fahrenheit together
    assert oval["protein_g"] >= 60 and oval["calories"] <= 1000


SERVED_AT = {
    "On the Oval": {"Scrambled Eggs", "Grilled Chicken", "Tofu Bowl", "Cheese Pizza"},
    "Clark Dining Hall": {"Chicken Satay"},
}


def test_plan_never_mixes_locations(client, campus):
    plans = by_location(post(client, {"protein_goal_g": 60, "max_calories": 1000}))
    assert plans["On the Oval"]["items"] and plans["Clark Dining Hall"]["items"]
    for name, plan in plans.items():
        assert {i["name"] for i in plan["items"]} <= SERVED_AT[name]


def test_pools_meals_and_reports_each_dish_meal(client, campus):
    # 73 g needs all four labelled dishes (13 + 30 + 18 + 12), across both meals.
    oval = by_location(post(client, {"protein_goal_g": 73, "max_calories": 1000}))[
        "On the Oval"
    ]
    meals = {i["name"]: i["meal"] for i in oval["items"]}
    assert meals == {
        "Scrambled Eggs": "Breakfast",
        "Grilled Chicken": "Lunch",
        "Tofu Bowl": "Lunch",
        "Cheese Pizza": "Lunch",
    }
    assert oval["status"] == "met"


def test_dish_served_at_two_meals_is_planned_once(client, campus, seed):
    seed.item(
        62, "Scrambled Eggs", "6|eggs|1 each", allergens=["egg"], diets=["vegetarian"]
    )
    oval = by_location(post(client, {"protein_goal_g": 73, "max_calories": 1000}))[
        "On the Oval"
    ]
    eggs = [i for i in oval["items"] if i["name"] == "Scrambled Eggs"]
    assert len(eggs) == 1 and eggs[0]["meal"] == "Breakfast"
    assert oval["candidates"] == 4 and oval["items_checked"] == 6


def test_meal_names_are_trimmed(client, campus):
    body = {"meals": ["  breakfast "], "protein_goal_g": 10, "max_calories": 1000}
    oval = by_location(post(client, body))["On the Oval"]
    assert [i["name"] for i in oval["items"]] == ["Scrambled Eggs"]


def test_location_with_no_menus_gets_a_none_plan(client, campus, seed):
    seed.location(9, "Tuffy's Diner", "tuffys")  # known, but no menu yet
    plans = post(
        client, {"protein_goal_g": 10, "max_calories": 1000}, location_id=9
    ).json()
    assert len(plans) == 1
    assert plans[0]["status"] == "none" and plans[0]["items_checked"] == 0


def test_calorie_limit_too_low_is_none_with_candidates(client, campus):
    oval = by_location(post(client, {"protein_goal_g": 10, "max_calories": 50}))[
        "On the Oval"
    ]
    assert oval["status"] == "none" and oval["items"] == []
    assert oval["candidates"] == 4  # dishes fit; the limit is what rules them out


def test_ranked_met_first_by_calories(client, campus):
    plans = post(client, {"protein_goal_g": 60, "max_calories": 1000}).json()
    assert [p["location_name"] for p in plans] == ["Clark Dining Hall", "On the Oval"]
    assert plans[0]["calories"] <= plans[1]["calories"]


def test_avoided_allergen_changes_the_answer(client, campus):
    plans = by_location(
        post(client, {"avoid": ["nuts"], "protein_goal_g": 60, "max_calories": 1000})
    )
    assert plans["Clark Dining Hall"]["status"] == "none"
    assert plans["Clark Dining Hall"]["items"] == []
    assert plans["On the Oval"]["status"] == "met"
    first = post(
        client, {"avoid": ["nuts"], "protein_goal_g": 60, "max_calories": 1000}
    ).json()[0]
    assert first["location_name"] == "On the Oval"


def test_diet_limits_dishes_to_tagged_ones(client, campus):
    oval = by_location(
        post(client, {"diets": ["vegan"], "protein_goal_g": 10, "max_calories": 1000})
    )["On the Oval"]
    assert [i["name"] for i in oval["items"]] == ["Tofu Bowl"]


def test_unlabelled_dish_never_planned_and_counts(client, campus):
    oval = by_location(post(client, {"protein_goal_g": 500, "max_calories": 10000}))[
        "On the Oval"
    ]
    assert "Mystery Salad" not in [i["name"] for i in oval["items"]]
    assert oval["items_checked"] == 5 and oval["candidates"] == 4
    assert oval["status"] == "short"


def test_meals_filter_is_case_insensitive(client, campus):
    oval = by_location(
        post(
            client, {"meals": ["breakfast"], "protein_goal_g": 10, "max_calories": 1000}
        )
    )["On the Oval"]
    assert [i["name"] for i in oval["items"]] == ["Scrambled Eggs"]
    assert oval["items_checked"] == 1


def test_location_id_limits_to_one(client, campus):
    plans = post(
        client, {"protein_goal_g": 10, "max_calories": 1000}, location_id=6
    ).json()
    assert [p["location_id"] for p in plans] == [6]


def test_unknown_location_is_404(client, campus):
    response = post(
        client, {"protein_goal_g": 10, "max_calories": 1000}, location_id=999
    )
    assert response.status_code == 404


def test_other_day_has_nothing_to_plan(client, campus):
    plans = post(
        client, {"protein_goal_g": 10, "max_calories": 1000}, date=WED.isoformat()
    ).json()
    assert {p["status"] for p in plans} == {"none"}
    assert all(p["date"] == "2026-10-07" for p in plans)


def test_planned_items_carry_full_menu_item(client, campus):
    oval = by_location(post(client, {"protein_goal_g": 10, "max_calories": 1000}))[
        "On the Oval"
    ]
    item = oval["items"][0]
    for key in (
        "id",
        "name",
        "course",
        "allergens",
        "diets",
        "nutrition",
        "meal",
        "diets_removed",
    ):
        assert key in item
    assert item["nutrition"]["protein_g"] is not None


def test_approved_label_review_removes_a_dish(client, campus, db):
    """A reviewer removed Tofu Bowl's vegan tag: the planner must respect it, like the filter does."""
    db.add(
        LabelReview(
            location_id=6,
            dish=dish_name("Tofu Bowl"),
            item_name="Tofu Bowl",
            tags=["vegan"],
            words=["honey"],
            ingredients_hash=ingredients_hash(
                None
            ),  # the seeded label has no ingredients
            status="approved",
            first_seen_at=datetime(2026, 10, 5, tzinfo=UTC),
            reason="ingredients list honey",
        )
    )
    db.commit()
    oval = by_location(
        post(client, {"diets": ["vegan"], "protein_goal_g": 10, "max_calories": 1000})
    )["On the Oval"]
    assert oval["status"] == "none"


@pytest.mark.parametrize(
    "body",
    [
        {"protein_goal_g": 10},  # missing max_calories
        {"max_calories": 1000},  # missing protein goal
        {"protein_goal_g": 0, "max_calories": 1000},
        {"protein_goal_g": 10, "max_calories": 0},
        {"protein_goal_g": 10, "max_calories": 20000},
        {"protein_goal_g": 10, "max_calories": 1000, "avoid": ["peanuts"]},
        {"protein_goal_g": 10, "max_calories": 1000, "diets": ["keto"]},
        {"protein_goal_g": 10, "max_calories": 1000, "max_items": 0},
        {"protein_goal_g": 10, "max_calories": 1000, "max_items": 11},
        {"protein_goal_g": 10, "max_calories": 1000, "meals": []},
        {"protein_goal_g": 10, "max_calories": 1000, "meals": [""]},
        {"protein_goal_g": 10, "max_calories": 1000, "meals": ["   "]},
        {"protein_goal_g": 10, "max_calories": 1000, "meals": ["x" * 51]},
        {"protein_goal_g": 1000.5, "max_calories": 1000},
        {
            "protein_goal_g": 10,
            "max_calories": 1000,
            "min_protein_g": 5,
        },  # unknown field
    ],
)
def test_bad_requests_are_rejected(client, campus, body):
    assert post(client, body).status_code == 422
