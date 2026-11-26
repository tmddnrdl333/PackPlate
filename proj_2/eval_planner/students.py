"""Simulated students for the planner eval. Simulated users, not real ones.

Restrictions come from the same published rates as PackPlate's own M0
(eval_loop2/simulation.json, drawn by eval_loop2.simulate.person). The claim is
about students *with* restrictions, so a student with none is redrawn. Each
student also gets a daily protein goal and a calorie limit, kept for all days.
A fixed seed gives the same students every run.
"""

import json
import random
from dataclasses import dataclass
from pathlib import Path

from app.services.filter_engine import Profile
from app.services.planner import Goal
from eval_loop2.simulate import load_config, person

SETTINGS = Path(__file__).parent / "settings.json"


@dataclass(frozen=True)
class Student:
    """One simulated student: their restrictions and their daily goal."""

    profile: Profile
    goal: Goal

    @property
    def group(self) -> str:
        """vegan, vegetarian, or other (allergies, pork, or halal only)."""
        for diet in ("vegan", "vegetarian"):
            if diet in self.profile.diets:
                return diet
        return "other"

    def describe(self) -> str:
        """The restrictions in words, e.g. "avoids nuts, is vegan"."""
        parts = [f"avoids {a}" for a in sorted(self.profile.avoid)]
        parts += [f"is {d}" for d in sorted(self.profile.diets)]
        return ", ".join(parts)


def load_settings(path: Path = SETTINGS) -> dict:
    """The eval settings in eval_planner/settings.json."""
    return json.loads(path.read_text(encoding="utf-8"))


def restricted_person(rng: random.Random, rates: dict) -> Profile:
    """One person drawn at the published rates, redrawn until they have a restriction."""
    while True:
        p = person(rng, rates)
        if p.avoid or p.diets:
            return p


def students(settings: dict, rates: dict | None = None) -> list[Student]:
    """All the simulated students. The same seed always gives the same students."""
    rates = rates if rates is not None else load_config()
    rng = random.Random(settings["seed"])
    lo_p, hi_p = settings["protein_goal_g"]
    lo_c, hi_c = settings["max_calories"]
    out = []
    for _ in range(settings["students"]):
        p = restricted_person(rng, rates)
        goal = Goal(
            protein_g=rng.randint(lo_p, hi_p),
            max_calories=rng.randrange(lo_c, hi_c + 1, settings["calorie_step"]),
            avoid=p.avoid,
            diets=p.diets,
            max_items=settings["max_items"],
        )
        out.append(Student(p, goal))
    return out
