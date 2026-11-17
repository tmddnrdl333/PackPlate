"""Daily meal planner route (Project 3, M2).

Thin: loads the day's menus (with approved label reviews applied, exactly as
the filter routes do) and hands each location's dishes to services/planner.py.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.repositories import label_reviews as reviews_repo
from app.repositories import locations as locations_repo
from app.repositories import menus as menus_repo
from app.schemas.locations import MenuItem
from app.schemas.planner import LocationPlan, PlanRequest
from app.services import planner
from app.services.hours import campus_time
from app.services.label_reviews import reviewed_items
from app.services.menus import menu_sort_key

router = APIRouter(prefix="/planner", tags=["planner"])


def _goal(request: PlanRequest) -> planner.Goal:
    return planner.Goal(
        protein_g=request.protein_goal_g,
        max_calories=request.max_calories,
        avoid=frozenset(request.avoid),
        diets=frozenset(request.diets),
        max_items=request.max_items,
    )


@router.post("/day", response_model=list[LocationPlan])
def plan_day(
    request: PlanRequest,
    on: date | None = Query(None, alias="date"),
    location_id: int | None = None,
    db: Session = Depends(get_db),
):
    """A one-location meal plan for `date` (default today) at every location, best first.

    Ranked: plans that meet the goal (fewest calories first), then plans that
    fall short (most protein first), then locations with nothing to plan.
    With `location_id`, only that location (404 if it doesn't exist; a known
    location with no menu that day gets a "none" plan).
    """
    if location_id is None:
        locations = locations_repo.list_locations(db)
    else:
        # Any known location, even one that hasn't published a menu yet ("none").
        location = locations_repo.get_location(db, location_id)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"location {location_id} not found"
            )
        locations = [location]
    day = on or campus_time().date()
    goal = _goal(request)
    wanted = {m.casefold() for m in request.meals} if request.meals else None
    approved = reviews_repo.approved(db)
    menus = (
        menus_repo.all_menus_on(db, day)
        if location_id is None
        else menus_repo.menus_on(db, location_id, day)
    )

    # Each location's dishes in menu order (breakfast before lunch...), and
    # which meal each dish is served at (the first, if it's served at several).
    dishes: dict[int, list] = {}
    meal_of: dict[int, str] = {}
    for menu in sorted(menus, key=menu_sort_key):
        if wanted is not None and menu.meal.casefold() not in wanted:
            continue
        for item in reviewed_items(menu, approved):
            dishes.setdefault(menu.location_id, []).append(item)
            meal_of[item.id] = menu.meal

    results = []
    for location in locations:
        items = dishes.get(location.id, [])
        result = planner.plan(items, goal)
        results.append((location.name, result, location.id, len(items)))
    results.sort(key=lambda r: planner.rank_key(r[0], r[1]))

    return [
        {
            "location_id": loc_id,
            "location_name": name,
            "date": day,
            "status": result.status,
            "items": [
                {
                    **MenuItem.model_validate(item, from_attributes=True).model_dump(),
                    "meal": meal_of[item.id],
                }
                for item in result.items
            ],
            "protein_g": result.protein_g,
            "calories": result.calories,
            "candidates": result.candidates,
            "items_checked": checked,
        }
        for name, result, loc_id, checked in results
    ]
