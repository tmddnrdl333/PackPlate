# 🐺 PackPlate 🍽️

<!-- Badges report the dev branch. Each links to its workflow runs on dev. -->
[![Tests](https://github.com/morgansimon425/PackPlate/actions/workflows/tests.yml/badge.svg?branch=dev)](https://github.com/morgansimon425/PackPlate/actions/workflows/tests.yml?query=branch%3Adev)
[![Test count](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/EthanGoodman/723b874f576ec1c7acbc27ac884ffeca/raw/packplate-tests.json)](https://github.com/morgansimon425/PackPlate/actions/workflows/tests.yml?query=branch%3Adev)
[![Coverage](https://codecov.io/gh/morgansimon425/PackPlate/branch/dev/graph/badge.svg)](https://app.codecov.io/gh/morgansimon425/PackPlate/tree/dev)
[![Ruff](https://github.com/morgansimon425/PackPlate/actions/workflows/ruff.yml/badge.svg?branch=dev)](https://github.com/morgansimon425/PackPlate/actions/workflows/ruff.yml?query=branch%3Adev)
[![Black](https://github.com/morgansimon425/PackPlate/actions/workflows/black.yml/badge.svg?branch=dev)](https://github.com/morgansimon425/PackPlate/actions/workflows/black.yml?query=branch%3Adev)
[![Prettier](https://github.com/morgansimon425/PackPlate/actions/workflows/prettier.yml/badge.svg?branch=dev)](https://github.com/morgansimon425/PackPlate/actions/workflows/prettier.yml?query=branch%3Adev)
[![ESLint](https://github.com/morgansimon425/PackPlate/actions/workflows/eslint.yml/badge.svg?branch=dev)](https://github.com/morgansimon425/PackPlate/actions/workflows/eslint.yml?query=branch%3Adev)
[![Typecheck](https://github.com/morgansimon425/PackPlate/actions/workflows/typecheck.yml/badge.svg?branch=dev)](https://github.com/morgansimon425/PackPlate/actions/workflows/typecheck.yml?query=branch%3Adev)
[![M0 loop 1](https://github.com/morgansimon425/PackPlate/actions/workflows/m0.yml/badge.svg?branch=dev)](https://github.com/morgansimon425/PackPlate/actions/workflows/m0.yml?query=branch%3Adev)
[![M0 loop 2](https://github.com/morgansimon425/PackPlate/actions/workflows/m0_loop2.yml/badge.svg?branch=dev)](https://github.com/morgansimon425/PackPlate/actions/workflows/m0_loop2.yml?query=branch%3Adev)
[![P3 M0 planner](https://github.com/tmddnrdl333/PackPlate/actions/workflows/m0_planner.yml/badge.svg?branch=main)](https://github.com/tmddnrdl333/PackPlate/actions/workflows/m0_planner.yml?query=branch%3Amain)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23521650.svg)](https://doi.org/10.5281/zenodo.23521650)

https://github.com/user-attachments/assets/c9b771b0-a093-43f9-bab0-dbc98d99fb92

A website that helps NC State students decide where to eat on campus. It puts
dining hours, menus, and nutrition information from every campus dining
location in one place, and filters the menus by dietary restrictions and goals
like allergies, vegetarian, halal, or a protein target. Students can enter
constraints for several people at once, so a group with different diets can
find a location where everyone has something to eat. Students can also report
how busy each location is.

## 🎯 M0 evals

### Project 3 M0: the meal planner

Our Project 3 work added a daily meal planner
([P3 M2](proj_2/docs/p3-m2-meal-planner.md)). It combines dishes at one
location to reach a student's protein goal under their calorie limit. Its M0
tests whether that still works once a student's restrictions remove dishes.

**The claim:** for a student with dietary restrictions and a daily protein
goal (60–150 g), the planner builds a plan from that day's campus menus that
meets the goal, stays under their calorie limit, and uses only dishes PackPlate
marks safe for them, on **at least 90% of student-days**.

| Target | Result | |
|---|---|---|
| **Useful:** ≥ 90% of student-days met | **84.5%** of 1,200 | ❌ missed |
| **Safe:** 0 planned dishes the filter doesn't call `fits` | **0** | ✅ met |
| **Safe:** 0 missed when the ingredients of 50 random planned dishes are read | **0** missed (44 ok, 6 unclear) | ✅ met |
| *Baseline: the single best dish (PackPlate before the planner)* | *2.7%* | |
| *After the descope: missed days that show the new goal warning* | ***186 of 186*** | ✅ |

- **Where it misses:** students with only allergies, halal, or pork
  restrictions reach their goal on **95%** of days. Vegetarian and vegan
  students reach it on only **56–57%**, because no single location's menu
  offers them more than about 94–109 g of protein a day. On every missed day,
  no location had any plan that met the goal, so this is a menu limit, not a
  planner bug.
- **Spiral review: descope, and warn.** The claim is narrowed to what the
  planner controls: when a location can reach the goal, the planner finds a
  safe plan that does. When none can, the planner page now says so, names the
  most protein one location offers, and has a button to use that as the goal.
  The warning is new Project 3 code, and it appears on all 186 missed days.
- **Safe, hand check:** 0 misses in 44 decided rows means the true miss rate
  is at most 6.6% (95% confidence), not that it's 0. It was read by Claude
  (AI) with the original team's loop 2 rules, and is **pending a team
  member's confirmation**.
- **Students:** 200 simulated students, **not real ones**. Each has at least
  one restriction, drawn at the same published rates as the loop 1 and loop 2
  evals below. Each student keeps one goal and calorie limit for six days.
- **Data:** both frozen snapshots already in the repo, Oct 12–14 and
  Oct 20–22, 2026. The eval calls the same `planner.plan()` function the API
  uses.
- **Labels one serving can't have** (e.g. "Sliced Mushrooms" with 162 g
  protein, from a whole-pan label) don't count toward a met plan.
- **Reproduce:** `cd proj_2 && python -m eval_planner.m0`, in about 40 s. The
  **P3 M0 planner** badge means the committed numbers reproduce, not that the
  targets were met.
- **Details:** [the plan, the result, the hand check, and the decision](proj_2/docs/p3-m0-planner-eval.md),
  [the result file](proj_2/eval_planner/results.json).

### Inherited from Project 2 (still runs)

The original team's M0 is unchanged. Both loops still run on this fork and
reproduce their committed numbers after our Project 3 changes (rechecked
2026-11-26 with `--check`). **Loop 2 measures today's PackPlate and meets both
of its targets.** Loop 1's missed Safe target is the historical result that led
to the loop 2 fixes.

#### Loop 1

**The claim**, posted in [issue #11](https://github.com/morgansimon425/PackPlate/issues/11)
before the first run: a group of friends with different diets can find
somewhere on campus where everyone can eat, using NC State's own data, without
PackPlate ever telling someone a dish is safe when it isn't.

| Target | Result | |
|---|---|---|
| **Safe:** 0 confirmed false fits | **6** in 7,926 "fits" answers checked | ❌ missed |
| **Useful:** at least 80% of simulated groups answered | **100%** of 1,000 groups | ✅ met |

- **Safe:** every "fits" answer's ingredient list was scanned, and a person
  read every flag. The 6 real ones come from NC State's own data missing an
  allergen icon, e.g. cooked chicken fat in a soup tagged Vegetarian, and whey
  in a pancake with no dairy icon. NetNutrition's own icon-only filter makes
  the same 6 mistakes.
- **Useful:** simulated groups of 2–5 people, with restriction rates from
  published studies. These are **simulated users, not real ones**.
- **Data:** a frozen snapshot of Oct 12–14, 2026, committed to the repo.
- **Reproduce:** `cd proj_2 && python -m eval.m0`. The **M0 loop 1** badge
  means the committed numbers reproduce, not that the targets were met.
- **Details:** [the plan](proj_2/docs/m0-eval.md),
  [the result](proj_2/eval/results.json), and the review decision in
  [issue #11](https://github.com/morgansimon425/PackPlate/issues/11).

#### Loop 2: after the fixes

Loop 1 showed that NC State's icons leave allergens out, so PackPlate now reads
the ingredient lists itself and flags what the icons miss
([#17](https://github.com/morgansimon425/PackPlate/pull/17), tuned in
[#20](https://github.com/morgansimon425/PackPlate/pull/20)), lets the team
correct a dish's tags by hand
([#19](https://github.com/morgansimon425/PackPlate/pull/19)), and warns on the
menu that labels can be wrong
([#23](https://github.com/morgansimon425/PackPlate/pull/23)). Loop 2 re-tests
today's PackPlate on new days, with targets posted in
[issue #26](https://github.com/morgansimon425/PackPlate/issues/26) before the
run. Because the new scanner was built from loop 1's word list, loop 2 doesn't
use a word list: a person read the ingredients of 50 random "fits" answers.

| Target | Result | |
|---|---|---|
| **Safe:** 0 missed in 50 random "fits" answers | **0** missed (45 ok, 5 unclear) | ✅ met |
| **Useful:** at least 80% of simulated groups answered | **90.2%** of 1,000 groups | ✅ met |

- **Safe:** 0 misses in 45 decided answers means the true miss rate is at most
  6.4% (95% confidence), not that it's 0. The 5 unclear answers list "natural
  flavors" for a pork, halal, vegan, or vegetarian profile, where the label
  can't tell.
- **Useful:** lower than loop 1's 100%. The days and the filter both changed,
  so the eval can't say how much of the drop each one caused.
- **Data:** a frozen snapshot of Oct 20–22, 2026, committed to the repo.
- **Reproduce:** `cd proj_2 && python -m eval_loop2.m0`. It has its own
  **M0 loop 2** badge and shares no code with loop 1.
- **Details:** [the plan and limits](proj_2/docs/m0-eval.md#loop-2-after-the-fixes)
  and [the result](proj_2/eval_loop2/results.json).

## 📚 Documentation

| | |
|---|---|
| [Why PackPlate](proj_2/docs/why.md) | The problem, who it's for, and the evidence that it works |
| [How to use it](proj_2/docs/how.md) | Worked examples: the website, the API, and common developer tasks |
| [Code reference](proj_2/docs/reference.md) | Every module, class, and function, generated from the code |
| [HTTP API](proj_2/docs/api.md) | Every endpoint and data model, generated from the API |
| [Install](INSTALL.md) | Getting PackPlate running on your machine |
| [Contributing](CONTRIBUTING.md) | Setup, tests, checkers, and how to make changes safely |
| [Code of conduct](CODE-OF-CONDUCT.md) · [License](LICENSE.md) · [Third-party libraries](THIRD_PARTY_LIBRARIES.md) | |

## 📁 Structure

```
proj_1b/    Project 1b — requirements
proj_2/     Project 2 — implementation (Next.js + FastAPI + Postgres)
```

## 🎓 Course

CSC 510 Software Engineering, NC State University, Fall 2026.
Course repository: https://github.com/txt/se26f
