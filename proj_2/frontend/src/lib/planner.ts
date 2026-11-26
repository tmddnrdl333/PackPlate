// Daily meal planner (Project 3, M2). Mirrors backend/app/schemas/planner.py
// field for field; if that changes, change this too.
import type { Allergen, Diet, MenuItem } from "./types";

export type PlanStatus = "met" | "short" | "none";

export interface PlanRequest {
  avoid: Allergen[];
  diets: Diet[];
  protein_goal_g: number; // reach at least this much
  max_calories: number; // stay at or under this
  max_items?: number; // 1-10, default 6
  meals?: string[]; // only these meals; omitted = all of that day's meals
}

export interface PlannedItem extends MenuItem {
  meal: string;
}

export interface LocationPlan {
  location_id: number;
  location_name: string;
  date: string; // YYYY-MM-DD
  status: PlanStatus;
  items: PlannedItem[];
  protein_g: number;
  calories: number;
  candidates: number; // dishes that were safe and had usable nutrition
  items_checked: number;
}

// Server-side limits (schemas/planner.py).
export const PLAN_LIMITS = {
  protein_goal_g: 1000,
  max_calories: 10000,
  max_items: 10,
} as const;

export const PLAN_DEFAULTS = {
  protein_goal_g: 100,
  max_calories: 2000,
  max_items: 6,
} as const;

// A form value the server would reject, as a sentence; null when it's fine.
export function validatePlan(request: PlanRequest): string | null {
  const { protein_goal_g: protein, max_calories: calories } = request;
  if (!Number.isFinite(protein) || protein <= 0) {
    return "Enter a protein goal above 0 g.";
  }
  if (protein > PLAN_LIMITS.protein_goal_g) {
    return `The protein goal can be at most ${PLAN_LIMITS.protein_goal_g} g.`;
  }
  if (!Number.isFinite(calories) || calories <= 0) {
    return "Enter a calorie limit above 0.";
  }
  if (calories > PLAN_LIMITS.max_calories) {
    return `The calorie limit can be at most ${PLAN_LIMITS.max_calories}.`;
  }
  const items = request.max_items ?? PLAN_DEFAULTS.max_items;
  if (!Number.isInteger(items) || items < 1 || items > PLAN_LIMITS.max_items) {
    return `Dishes must be a whole number from 1 to ${PLAN_LIMITS.max_items}.`;
  }
  return null;
}

// How far a plan got toward the goal, in whole percent. Rounded down, and a
// plan that falls short never reads 100%.
export function progress(plan: LocationPlan, goal: number): number {
  const percent = Math.floor((plan.protein_g / goal) * 100);
  return plan.status === "met" ? 100 : Math.min(99, percent);
}

// When no location can reach the goal (Project 3 M0 descope): the student's
// goal is beyond what any one location's menu offers them that day. The M0
// eval found every missed day was like this, mostly for vegetarian and vegan
// students with high goals, so the page says so and offers a goal that works.
export interface GoalWarning {
  goal: number; // what the student asked for
  reachable: number; // the most protein any one location offers them, in g
  location: string; // where that is
  suggested: number; // the highest whole-gram goal that location fully meets
  plantBased: boolean; // vegetarian or vegan
}

export function goalWarning(
  plans: LocationPlan[],
  goal: number,
  diets: readonly Diet[],
): GoalWarning | null {
  if (plans.some((p) => p.status === "met")) return null;
  let top: LocationPlan | null = null;
  for (const plan of plans) {
    if (plan.status !== "short") continue;
    if (top === null || plan.protein_g > top.protein_g) top = plan;
  }
  if (top === null) return null;
  return {
    goal,
    reachable: top.protein_g,
    location: top.location_name,
    suggested: Math.floor(top.protein_g),
    plantBased: diets.includes("vegan") || diets.includes("vegetarian"),
  };
}
