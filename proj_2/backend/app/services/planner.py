"""Daily meal planner (Project 3, M2). Pure functions, no database.

Given one student's needs and one location's menus for one day, pick a set of
dishes that reaches a daily protein goal without going over a calorie limit.

The rules (spec: proj_2/docs/p3-m2-meal-planner.md):

Safety, inherited from filter_engine (never second-guessed here)
    a dish is a candidate only if filter_engine.check() says "fits" for the
    student's allergens and diets, AND its label has usable protein and
    calories (no label, a placeholder label, or a nutrient NC State flags as
    incomplete makes it "incomplete", so it is never planned)
One location per plan
    a plan never mixes locations. Stations inside one location (On the Oval's
    Flashpoint and Fahrenheit) are the same location, so they mix freely.
    All of that location's meals that day are pooled, unless `meals` narrows it.
Same dish twice
    the same dish served at two meals (same name and serving size) counts once
The search
    0/1 knapsack, at most `max_items` dishes, each at most once.
    "met":   protein >= goal and calories <= limit. Among those, the fewest
             calories, then the fewest dishes.
    "short": no plan meets the goal; the most protein that fits the calorie
             limit and dish cap instead.
    "none":  no candidate dish at all (nothing safe with usable nutrition).
    Protein is counted in whole grams rounded down, so a "met" plan's real
    total is never below the goal. Ties break on input order, so the same
    input always gives the same plan.
"""

import math
from dataclasses import dataclass, field

from app.services import filter_engine
from app.services.label_reviews import dish_name

MET, SHORT, NONE = "met", "short", "none"
DEFAULT_MAX_ITEMS = 6
MAX_ITEMS_LIMIT = 10


@dataclass(frozen=True)
class Goal:
    """One student's day: who they are (allergens, diets) and what they want to reach."""

    protein_g: float  # daily protein goal, at least this
    max_calories: float  # daily calorie limit, at most this
    avoid: frozenset[str] = frozenset()  # filter_engine.ALLERGEN_KEYS
    diets: frozenset[str] = frozenset()  # filter_engine.DIET_KEYS
    max_items: int = DEFAULT_MAX_ITEMS  # at most this many dishes

    def __post_init__(self):
        if not self.protein_g > 0:
            raise ValueError("protein_g must be > 0")
        if not self.max_calories > 0:
            raise ValueError("max_calories must be > 0")
        if not 1 <= self.max_items <= MAX_ITEMS_LIMIT:
            raise ValueError(f"max_items must be 1..{MAX_ITEMS_LIMIT}")
        unknown = (self.avoid - set(filter_engine.ALLERGEN_KEYS)) | (
            self.diets - set(filter_engine.DIET_KEYS)
        )
        if unknown:
            raise ValueError(f"unknown allergen or diet: {sorted(unknown)}")


@dataclass
class Plan:
    """The planner's answer for one location on one day."""

    status: str  # MET, SHORT, or NONE
    items: list = field(default_factory=list)  # the picked dishes, in input order
    protein_g: float = 0.0  # totals of the picked dishes
    calories: float = 0.0
    candidates: int = 0  # how many dishes were safe and plannable


def safety_profile(goal: Goal) -> filter_engine.Profile:
    """The filter_engine profile a dish must "fit" to be planned.

    min_protein_g=0 and max_calories=inf never reject a dish on their own;
    they make filter_engine demand a usable protein and calorie number, so a
    dish with no label or a placeholder label comes back "incomplete".
    """
    return filter_engine.Profile(
        avoid=goal.avoid,
        diets=goal.diets,
        min_protein_g=0,
        max_calories=math.inf,
    )


def dish_key(item) -> tuple[str, str]:
    """Two menu rows are the same dish if name and serving size match.

    Names are matched the way label reviews match them (label_reviews.dish_name).
    """
    serving = getattr(item, "serving_size", None) or ""
    return (dish_name(item.name), dish_name(serving))


def candidates(items, goal: Goal) -> list:
    """The dishes a plan may use, in input order: safe, usable nutrition, one per dish."""
    profile = safety_profile(goal)
    seen: set[tuple[str, str]] = set()
    out = []
    for item in items:
        key = dish_key(item)
        if key in seen:
            continue
        if filter_engine.check(item, profile).verdict != filter_engine.FITS:
            continue
        seen.add(key)
        out.append(item)
    return out


def _totals(items) -> tuple[float, float]:
    return (
        sum(i.nutrition.protein_g for i in items),
        sum(i.nutrition.calories for i in items),
    )


def plan(items, goal: Goal) -> Plan:
    """The best plan from one location's dishes for one day (see the module docstring)."""
    pool = candidates(items, goal)
    if not pool:
        return Plan(NONE)

    target = math.ceil(goal.protein_g)  # whole grams; protein is floored below
    k_max = goal.max_items
    # Dishes that can't help: over the limit alone, or under 1 g of protein
    # (they only add calories, so the best plan never needs them).
    usable = [
        (i, math.floor(i.nutrition.protein_g), i.nutrition.calories)
        for i in pool
        if i.nutrition.calories <= goal.max_calories and i.nutrition.protein_g >= 1
    ]

    # best[k][p] = (calories, picks) for exactly k dishes whose floored protein,
    # capped at target, is p. Fewest calories wins; ties keep the earlier picks.
    best: list[list[tuple[float, tuple[int, ...]] | None]] = [
        [None] * (target + 1) for _ in range(k_max + 1)
    ]
    best[0][0] = (0.0, ())
    for idx, (_, protein, calories) in enumerate(usable):
        for k in range(k_max - 1, -1, -1):  # 0/1: each dish once
            row, nxt = best[k], best[k + 1]
            for p in range(target, -1, -1):
                state = row[p]
                if state is None:
                    continue
                cal = state[0] + calories
                if cal > goal.max_calories:
                    continue
                q = min(target, p + protein)
                if nxt[q] is None or cal < nxt[q][0]:
                    nxt[q] = (cal, state[1] + (idx,))

    met = [best[k][target] for k in range(1, k_max + 1) if best[k][target]]
    if met:
        # Fewest calories, then fewest dishes (k is the tuple length).
        chosen = min(met, key=lambda s: (s[0], len(s[1])))
        status = MET
    else:
        reachable = [
            (p, s) for k in range(1, k_max + 1) for p, s in enumerate(best[k]) if s
        ]
        if not reachable:
            return Plan(SHORT, candidates=len(pool))
        top = max(p for p, _ in reachable)
        chosen = min(
            (s for p, s in reachable if p == top), key=lambda s: (s[0], len(s[1]))
        )
        status = SHORT

    picked = [usable[i][0] for i in chosen[1]]
    protein, calories = _totals(picked)
    return Plan(status, picked, protein, calories, len(pool))


def rank_key(location_name: str, result: Plan):
    """Sort order across locations: met (fewest calories), then short (most protein), then none."""
    order = {MET: 0, SHORT: 1, NONE: 2}[result.status]
    if result.status == MET:
        return (order, result.calories, location_name)
    return (order, -result.protein_g, location_name)
