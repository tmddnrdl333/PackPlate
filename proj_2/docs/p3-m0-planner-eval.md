# Project 3 · M0 — Meal planner eval

This is the M0 claim for **our Project 3 work**, the daily meal planner
([P3 M2](p3-m2-meal-planner.md)). The original team's M0 (loop 1 and loop 2,
[m0-eval.md](m0-eval.md)) is unchanged. It still runs, and its numbers are
reported in the README.

## The claim

> For a student with dietary restrictions and a daily protein goal, the meal
> planner builds a plan from that day's campus menus that meets the goal, stays
> under their calorie limit, and uses only dishes PackPlate marks safe for
> them, on **at least 90% of student-days**.

**Why this claim:** the planner only matters if the menus still have enough
protein after filtering out everything a restricted student can't eat. If a
vegan student with a nut allergy almost never reaches their goal, the feature
fails the people it was built for.

## Targets

| | Target | How it's measured |
|---|---|---|
| **Useful** | ≥ 90% of student-days `met` | Some location's plan from `planner.plan()` has protein ≥ goal and calories ≤ limit, and **every dish in it has a plausible label** |
| **Safe (automatic)** | 0 unsafe planned dishes | Every dish in every plan is re-checked with `filter_engine.check()` against the student's full profile |
| **Safe (by hand)** | 0 missed in 50 | A person reads the ingredients of 50 random planned (dish, student) pairs |
| **Baseline** | reported, no target | The single best dish, which is what PackPlate offered before the planner: one safe, plausible dish alone reaches the goal under the limit |
| **Warning** (added by the descope decision) | reported | Of the missed student-days, how many show the planner page's "no location can reach your goal" warning |

A missed target is a spiral review, not a failure. We report the number and
record a persevere / re-plan / descope decision (below).

## Design

| Question | Decision |
|---|---|
| Which code is measured? | `app.services.planner.plan()`, the same function `POST /planner/day` calls, on items built by the original team's `eval_loop2.snapshot.packplate_item`, so approved label reviews are applied as the API applies them. |
| One location or any? | **One location per plan** (decided in P3 M2). A student-day counts if *any* location's plan meets the goal, because the website lists every location's plan. |
| Which days? | All six frozen days in the repo: Oct 12–14 (`eval/data`) and Oct 20–22 (`eval_loop2/data`). |
| Oct 12–14 is an older export | It has no `ingredient_flags`. Production computes them as `matched_terms(ingredients)` (`ingestion/normalize.py`), and so does the eval, so the filter sees what it would see live. That export also has no `missing_fields` or `serving_size`, so NC State's incomplete-nutrient flags are unknown for those three days. |
| Who are the students? | 200 simulated students. **Simulated, not real.** Restrictions are drawn at the published rates PackPlate's M0 uses (`eval_loop2/simulation.json`: Gupta 2019, Pew, Gallup), and a student with no restriction is redrawn, because the claim is about restricted students. |
| Goal and limit | Protein goal: a whole number of grams from 60 to 150. Calorie limit: 1,800 to 2,800 in steps of 100. Each student keeps both for all six days. `max_items` is 6, the API's default. Seed 3. |
| Unit | A **student-day**: 200 × 6 = 1,200. |
| Implausible labels | NC State sometimes puts a whole pan's or case's label on one dish: Sliced Mushrooms at 162 g protein, Philly-Style Chicken at 769 g, Cheeseburger at 141 g. The planner trusts them, as the filter does, so a plan using one isn't a meal anyone can eat. A plan counts only if every dish has protein ≤ 100 g, calories ≤ 2,000, and protein × 4 ≤ calories. |
| Hand check | 50 pairs drawn with seed 2026 from every (dish, student) pair in a usable `met` plan. Pairs with no ingredient text are left out and counted. The sheet shows the student's restrictions, the dish, and the full ingredients, but not PackPlate's icons or flags. |

### Changes from the first draft of this plan, and why

The first draft (Nov 25) was reviewed against the code and a quick probe
run on the snapshots. These are method fixes; **the 90% target and the
60–150 g goal range are unchanged**.

1. **Only restricted students.** At the published rates, about 85% of people
   have no restriction, and they always reach the goal. Counting them would
   measure unrestricted students, not the claim.
2. **The plausible-label rule.** In the probe, the "single best dish" baseline
   looked like 92% only because of whole-pan labels. Without them it is near 0%.
3. **A hand check for safety.** The planner only picks dishes the filter calls
   `fits`, so "0 dishes marked `conflicts` or `incomplete`" can only fail if
   there's a bug. It stays as an automatic regression check. The safety claim
   that *can* fail is the hand check, as in the original team's loop 2.
4. **The open "one hall or any location" question** was already settled by
   P3 M2: one location per plan.

**Pre-registration:** the original team posted targets in an issue before
running. Issues are disabled on our fork, so the targets are recorded in this
file. The probe run happened before the targets were frozen here; it informed
the method fixes above, but not the threshold.

## Result (2026-11-26)

`cd proj_2 && python -m eval_planner.m0`: 1,200 student-days.

| | Planner | Single best dish | Student-days |
|---|---|---|---|
| **All restricted students** | **84.5%** | 2.7% | 1,200 |
| Allergies / halal / pork only | 95.0% | 3.6% | 876 |
| Vegetarian | 55.9% | 0% | 270 |
| Vegan | 57.4% | 0% | 54 |
| Goal 60–90 g | 100% | 8.7% | 366 |
| Goal 91–120 g | 87.8% | 0% | 450 |
| Goal 121–150 g | 65.9% | 0% | 384 |

The rate is 83.5% to 86.5% on each of the six days, so no single day drives it.

| Target | Result | |
|---|---|---|
| **Useful:** ≥ 90% of student-days | **84.5%** | ❌ missed |
| **Safe (automatic):** 0 unsafe planned dishes | **0** | ✅ met |
| **Safe (by hand):** 0 missed in 50 | **0** missed (44 ok, 6 unclear) | ✅ met |

- **The planner beats the baseline by a wide margin.** One dish alone almost
  never reaches 60–150 g of protein (2.7%). Combining dishes reaches it on
  84.5% of days.
- **The miss is a menu limit, not a planner bug.** For students with only
  allergies, halal, or pork restrictions, the planner meets the goal on 95% of
  days. Vegetarian and vegan students fall to about 56–57%, because the most
  protein the menus allow them is about 94–109 g a day at one location
  (P3 M2 spec), and a third of goals are above 120 g. On **every** missed
  student-day, no location had any plan that met the goal: the planner's
  search is exact, and the rate is the same with or without the
  plausible-label rule.
- **Safe:** 0 misses in 44 decided pairs means the true miss rate is at most
  **6.6%** (95% confidence), not that it is 0.

### The hand check

The sheet is `eval_planner/data/sample.csv`: 50 (dish, student) pairs drawn
with seed 2026 from the 2,109 pairs in usable `met` plans. 49 more pairs had no
ingredient text and couldn't be drawn.

**Who read it:** Claude (an AI assistant) read every row on 2026-11-26, using
the original team's loop 2 rules. A team member should re-read the 6 unclear
rows and spot-check the rest, then edit the sheet if they disagree and rerun
the eval. **AI-assisted, pending human confirmation.**

Rules, the same as loop 2 ([m0-eval.md](m0-eval.md)) plus one:

- "Natural flavors" is `unclear` for halal, pork, vegan, and vegetarian
  students, and `ok` for allergens. US law requires allergens to be named even
  inside flavorings (FALCPA, and the FASTER Act for sesame).
- "May contain" cross-contact warnings are `ok`. The filter makes no claim
  about cross-contact, and loop 2 marked its "may contain eggs" pizza row `ok`
  for an egg-avoiding profile.
- **New:** cheese listing "enzymes" is `unclear` for vegetarians, because it
  may be animal rennet and the label doesn't say.

The 6 unclear rows: Cheese Pizza and Mozzarella Stuffed Shells (vegetarian:
natural flavors, cheese enzymes); Mediterranean Panini (vegetarian: Pecorino
Romano and Parmesan enzymes); Hearty Plant-Powered Shepherd's Pie and Indian
Butter Chicken (halal: natural flavor); Cumin Black Beans (vegan: natural
flavor in the vegetable base). If all 6 were really misses, Safe would be
missed.

### Spiral review: descope, and warn

**Decision (2026-11-26): descope.** The planner can't make the campus menus
offer more protein, so the claim is narrowed to what it controls:

> For a restricted student whose goal some campus location can reach that
> day, the planner finds a safe plan that meets it; and when no location can,
> the planner page says so and offers the highest goal that does work.

The first part holds on every one of the 1,200 student-days: every miss was a
day when no location had any plan that met the goal. For the second part we
built the **goal warning**, which is new Project 3 code. When no location's
plan is `met` and at least one is `short`, the planner page says:

- "No dining location can reach *X* g of protein for you on this day."
- "The most any one location offers within your limits is *Y* g (*location*)."
- For a vegetarian or vegan student, it adds that campus menus have few
  high-protein plant-based dishes.

A **"Use a *Y* g goal"** button then sets the goal to the highest whole gram
that location meets.

| Warning check | Result |
|---|---|
| Missed student-days that show the warning | **186 of 186 (100%)** |

The warning was added after the first result, so this check is a measurement
of the fix, not a pre-registered target. The 84.5% stays as this loop's
Useful result. The code is in `goalWarning()` in `frontend/src/lib/planner.ts`
(7 tests in `frontend/tests/planner.test.ts`) and is shown in
`frontend/src/components/MealPlanner.tsx`. The eval mirrors its condition in
`student_day()`.

**Next loop:** measure the narrowed claim on a newly exported snapshot, with
targets posted before the run.

## Reproduce

```bash
cd proj_2
python -m eval_planner.m0            # print and write eval_planner/results.json
python -m eval_planner.m0 --check    # fail if the result differs (what CI runs)
pytest eval_planner                  # the eval's own tests
```

CI: [`.github/workflows/m0_planner.yml`](../../.github/workflows/m0_planner.yml)
(badge **P3 M0 planner**). A pass means the committed numbers reproduce, not
that the targets were met. The run takes about 40 s.

### Changing a hand-check decision

Edit `decision` (`ok`, `missed`, or `unclear`) and `note` in
`eval_planner/data/sample.csv`. Then run `python -m eval_planner.m0` and
commit `results.json` with the sheet. **Don't** rerun `eval_planner.sample`:
it refuses to overwrite the sheet, so the draw stays fixed.

## Files

New: `eval_planner/` (`m0.py`, `students.py`, `snapshot.py`, `sample.py`,
`settings.json`, `results.json`, `data/sample.csv`, `tests/`),
`.github/workflows/m0_planner.yml`, `frontend/tests/planner.test.ts`, and this
doc. Changed, in our own Project 3 files: `frontend/src/lib/planner.ts`
(`goalWarning`) and `frontend/src/components/MealPlanner.tsx` (the warning
replaces the generic "try a lower goal" banner). Changed, additions only:
`.github/workflows/tests.yml` (runs `pytest eval_planner`, counts it in the
badge and coverage), `docs/generate.py` (lists the package), and the
regenerated `docs/reference.md`. No original-team file's logic was changed.
