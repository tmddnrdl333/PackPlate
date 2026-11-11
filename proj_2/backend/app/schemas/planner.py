"""Request and response models for the daily meal planner (Project 3, M2).

Like the filter endpoints, the request is checked strictly: an unknown field,
allergen, or diet is rejected (422), never ignored, and nothing is stored.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.filters import Allergen, Diet
from app.schemas.locations import MenuItem
from app.services.planner import DEFAULT_MAX_ITEMS, MAX_ITEMS_LIMIT


class PlanRequest(BaseModel):
    """One student's day: allergens and diets (as in a filter profile) plus daily goals."""

    model_config = ConfigDict(extra="forbid")

    avoid: list[Allergen] = []  # allergens to avoid
    diets: list[Diet] = []  # diets every planned dish must meet
    protein_goal_g: float = Field(gt=0, le=1000)  # reach at least this much
    max_calories: float = Field(gt=0, le=10000)  # stay at or under this
    max_items: int = Field(DEFAULT_MAX_ITEMS, ge=1, le=MAX_ITEMS_LIMIT)
    # Only plan from these meals (e.g. ["Lunch", "Dinner"]), case-insensitive.
    # Omitted = every meal that location serves that day.
    meals: list[str] | None = Field(None, min_length=1, max_length=10)


class PlannedItem(MenuItem):
    """A dish in a plan: the menu item, plus which meal it is served at."""

    meal: str


class LocationPlan(BaseModel):
    """The planner's answer for one location on one day."""

    location_id: int
    location_name: str
    date: date
    status: Literal["met", "short", "none"]
    items: list[PlannedItem]  # the dishes; every one "fits" the student
    protein_g: float  # totals of `items`
    calories: float
    candidates: int  # dishes that were safe and had usable nutrition
    items_checked: int  # every dish served there that day (meals filter applied)
