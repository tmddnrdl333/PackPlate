# Project 3 · M2 — Daily meal planner

**Status (2026-11-11):** backend, website page, and tests built on branch
`m2-meal-planner` (GitHub: tmddnrdl333). This is **new Project 3 work** on top of
the forked PackPlate (fork point: tag `fork-point`); no original file's logic
was changed.

> Naming: the original team's docs `m1`–`m4` are *their* Project 2
> milestones. Files for our Project 3 work start with `p3-`.

## Goal

PackPlate's filter checks **one dish at a time** (`min_protein_g` means "this
dish has at least X g"). A student with a daily target — *"120 g protein
today, vegetarian, no nuts, under 2,000 calories"* — still has to add dishes up
by hand. The planner **combines dishes** from one dining location into a
day's plan that reaches the goal, using only dishes PackPlate already says
**fit** that student.

## Decisions

| Question | Decision |
|---|---|
| What is "one location"? | One row of `locations` (a NetNutrition unit). **Stations inside it mix freely**: On the Oval's Flashpoint, Fahrenheit, Gravity, and Newton's are all location 6. **Locations never mix**: a plan never combines On the Oval and Clark. |
| Which meals? | All of that location's menus on that day are pooled (Breakfast, Lunch, Dinner, and NC State's extra menus like "Daily" or "Gluten Friendly"). The optional `meals` field narrows it, e.g. `["Lunch", "Dinner"]` (case-insensitive). |
| Which dishes are allowed? | Only dishes where `filter_engine.check()` says **`fits`** for the student's `avoid` + `diets`, **and** whose label has usable protein and calories. The planner never second-guesses safety; it inherits every rule in `filter_engine.py` (ingredient flags, unrecognized traits, approved label reviews, placeholder labels). |
| Same dish at two meals? | Counts once (same name and serving size, matched like label reviews match dishes). |
| How many dishes? | At most `max_items` (default 6, 1–10), each at most once. |
| What does "best" mean? | Among plans that **meet** the goal (protein ≥ goal, calories ≤ limit): **fewest calories**, then fewest dishes. If none meets it: **most protein** within the limits ("short"). |
| Sodium, hours, crowd level? | Not in this milestone. The plan is for the whole day, so "open right now" doesn't apply. |
| Privacy | Like the filter: the request is never stored. The website pre-fills allergies/diets from the profile saved in the browser (My diet). |

## How it works

`backend/app/services/planner.py` — pure functions, no database:

1. **Candidates** = dishes that pass the safety rule above, de-duplicated, in input order.
2. **Search** = 0/1 knapsack by dynamic programming over *(dishes used, protein so far)*,
   keeping the fewest calories for each state.
   - Protein is counted in **whole grams rounded down**, and the goal is
     rounded **up**, so a plan reported as `met` really has at least the goal.
   - Dishes under 1 g of protein or over the calorie limit on their own are skipped:
     they can never help.
   - Cost: dishes × `max_items` × goal. A full campus day (24 locations) takes
     ~0.1–0.4 s on a laptop.
3. **Ties** break on input order, so **the same input always gives the same plan**.

Status per location: `met`, `short` (some plan, below goal), or `none`
(nothing safe with a usable label).

## HTTP API

`POST /planner/day?date=YYYY-MM-DD&location_id=N`

- `date`: optional, default today (campus time).
- `location_id`: optional; only that location (404 if unknown).

Request body (unknown fields, allergens, or diets → **422**):

```json
{
  "avoid": ["nuts"],
  "diets": ["vegetarian"],
  "protein_goal_g": 90,
  "max_calories": 2000,
  "max_items": 6,
  "meals": ["Breakfast", "Lunch"]
}
```

| Field | Rule |
|---|---|
| `avoid` | allergen keys, same as the filter: dairy, egg, gluten, nuts, pork, seafood, sesame, soy |
| `diets` | halal, vegan, vegetarian (all required) |
| `protein_goal_g` | required, > 0, ≤ 1000 |
| `max_calories` | required, > 0, ≤ 10000 |
| `max_items` | optional, 1–10, default 6 |
| `meals` | optional, 1–10 meal names |

Response: one entry per location, **ranked** — `met` (fewest calories first),
then `short` (most protein first), then `none`; ties by name.

```json
[
  {
    "location_id": 4,
    "location_name": "University Towers Dining Hall",
    "date": "2026-11-10",
    "status": "met",
    "items": [
      { "id": 123, "name": "Freshly Scrambled Eggs", "meal": "Breakfast",
        "course": "Home Style Entree", "nutrition": { "protein_g": 13, "calories": 140, "...": "..." },
        "...": "every MenuItem field" }
    ],
    "protein_g": 92.0,
    "calories": 1170.0,
    "candidates": 83,
    "items_checked": 222
  }
]
```

Every planned item is a full `MenuItem` (as in `/locations/{id}/menus`) plus `meal`.

## Python API (for M0 and other code)

The M0 eval should call the **same function** the API uses, on the frozen
snapshot, so its number measures the real feature. The original team's
`eval_loop2/snapshot.py` already turns snapshot items into exactly what the
API hands the planner (approved label reviews applied):

```python
from eval_loop2.snapshot import approved_reviews, load, packplate_item
from app.services.planner import MET, Goal, plan

snapshot = load()
approved = approved_reviews(snapshot)
goal = Goal(protein_g=120, max_calories=2000,
            avoid=frozenset({"nuts"}), diets=frozenset({"vegetarian"}))

for day in snapshot["days"]:
    by_location = {}
    for menu in snapshot["menus"]:
        if menu["date"] != day:
            continue
        loc = menu["location_id"]
        by_location.setdefault(loc, []).extend(
            packplate_item(item, loc, snapshot, approved) for item in menu["items"]
        )
    results = {loc: plan(items, goal) for loc, items in by_location.items()}
    met = [loc for loc, r in results.items() if r.status == MET]
```

Run from `proj_2/` with `PYTHONPATH=backend:.` (the venv active).

- `Goal(protein_g, max_calories, avoid=frozenset(), diets=frozenset(), max_items=6)`
  raises `ValueError` on bad values (same limits as the API).
- `plan(items, goal) -> Plan(status, items, protein_g, calories, candidates)`.
  `items` is any iterable of objects with `.name`, `.serving_size`,
  `.allergens`, `.diets`, `.unrecognized_traits`, `.nutrition` (as
  `filter_engine.check()` expects). Pass **one location's** dishes for one
  day; the caller decides how to combine locations (e.g. "any location met").
- `rank_key(location_name, plan)` gives the API's ordering.

### Numbers M0 should know before setting targets

Max protein reachable on the loop 2 snapshot (Oct 20–22), 2,000 kcal, 6 dishes,
best location per day:

| Profile | Day 1 | Day 2 | Day 3 |
|---|---|---|---|
| no restrictions | 313 g | 329 g | 196 g |
| vegetarian + no nuts | 99 g | 106 g | 109 g |
| vegan | 94 g | 94 g | 94 g |

So a goal drawn from 60–150 g will often be **unreachable** for vegetarian or
vegan students on these menus — that is a real finding, not a planner bug.
The M0 plan should decide (and post in its issue *before* running) how goals
are drawn and what counts as a pass.

## Website

`/planner` ("Plan my day" in the header): allergies and diets (pre-filled from
My diet, not saved back), protein goal, calorie limit, most dishes, and an
optional day. Shows the top 3 plans in full — each dish with its meal,
station, protein, calories, and a ✓ Fits badge — and lists the rest by name.
If no location meets the goal, it shows the closest plans and says so.

## Tests

`backend/tests/test_planner.py` (43, no database) and
`backend/tests/test_planner_api.py` (24, test database). They cover:

- **Safety:** avoided allergens, untagged diets, vegan-counts-as-vegetarian,
  unrecognized traits, ingredient flags doubting a tag, no label, missing or
  flagged protein/calories, placeholder labels, approved label reviews — and a
  check that every planned dish is `fits`.
- **Search:** meets goal under the limit, fewest calories, fewer dishes on a
  tie, calorie limit inclusive, `max_items`, each dish once, same dish at two
  meals counts once, fractional protein never overstated, zero-protein dishes
  skipped, best "short" plan, empty menus, deterministic output, and a
  **brute-force cross-check** on small menus.
- **API:** stations mix within a location, locations never mix, meal pooling
  and the `meals` filter, ranking, `location_id` and 404, other days, full
  `MenuItem` fields, and 11 kinds of rejected requests (422).

Run: `cd proj_2/backend && pytest tests/test_planner.py tests/test_planner_api.py`
(API tests need `TEST_DATABASE_URL`, see CONTRIBUTING.md).

## Files

New: `backend/app/services/planner.py`, `backend/app/schemas/planner.py`,
`backend/app/api/planner.py`, the two test files above,
`frontend/src/app/planner/page.tsx`, `frontend/src/components/MealPlanner.tsx`,
`frontend/src/lib/planner.ts`, and this doc.

Changed (one line each): `backend/app/main.py` (register the router),
`frontend/src/lib/api.ts` (`planDay`), `frontend/src/components/SiteHeader.tsx`
(nav link).

## Known limits

- **NC State's labels can be odd**, and the planner trusts them as the filter
  does. Seen on 2026-11-10: "Lettuce" at the Gluten-Friendly station with 32 g
  protein and 340 kcal, "Pico De Gallo" with 25 g / 630 kcal. These look like
  NC State attaching a whole dish's label to one component.
- One serving of each dish; no "two portions of chicken".
- The plan ignores opening hours and crowd levels (it plans a whole day).
- Calories and protein only; sodium, fat, and carbs aren't goals yet.

## Next

- M3 can sort these plans by walking distance (`location_id` is in every plan).
- Possible follow-ups: per-meal plans, portions, sodium as a goal.
