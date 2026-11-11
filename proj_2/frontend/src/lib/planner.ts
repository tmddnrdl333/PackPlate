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

// "84 of 100 g": how far a plan got toward the goal, for the summary line.
export function progress(plan: LocationPlan, goal: number): number {
  return Math.min(100, Math.round((plan.protein_g / goal) * 100));
}
