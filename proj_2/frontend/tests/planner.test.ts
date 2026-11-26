import assert from "node:assert/strict";
import { test } from "node:test";
import { goalWarning, type LocationPlan } from "../src/lib/planner.ts";

function plan(
  name: string,
  status: LocationPlan["status"],
  protein_g: number,
): LocationPlan {
  return {
    location_id: name.length,
    location_name: name,
    date: "2026-10-20",
    status,
    items: [],
    protein_g,
    calories: 1500,
    candidates: 5,
    items_checked: 50,
  };
}

test("no warning when any location meets the goal", () => {
  const plans = [plan("Clark", "short", 80), plan("Fountain", "met", 121)];
  assert.equal(goalWarning(plans, 120, ["vegan"]), null);
});

test("no warning when nothing could be planned at all", () => {
  // The page already explains "none" plans (no menus, nothing fits).
  assert.equal(goalWarning([plan("Clark", "none", 0)], 120, []), null);
  assert.equal(goalWarning([], 120, []), null);
});

test("warns with the most protein any one location offers", () => {
  const plans = [
    plan("Clark", "short", 88.5),
    plan("Fountain", "short", 94.2),
    plan("Case", "none", 0),
  ];
  assert.deepEqual(goalWarning(plans, 130, ["vegan"]), {
    goal: 130,
    reachable: 94.2,
    location: "Fountain",
    suggested: 94,
    plantBased: true,
  });
});

test("suggested goal is rounded down, so the top plan meets it", () => {
  const warning = goalWarning([plan("Clark", "short", 99.9)], 120, []);
  assert.equal(warning?.suggested, 99);
  assert.ok((warning?.suggested ?? Infinity) <= 99.9);
});

test("a tie keeps the first location in the list", () => {
  const plans = [plan("Clark", "short", 90), plan("Fountain", "short", 90)];
  assert.equal(goalWarning(plans, 120, [])?.location, "Clark");
});

test("plant-based flag follows the diets", () => {
  const plans = [plan("Clark", "short", 90)];
  assert.equal(goalWarning(plans, 120, ["vegetarian"])?.plantBased, true);
  assert.equal(goalWarning(plans, 120, ["halal"])?.plantBased, false);
  assert.equal(goalWarning(plans, 120, [])?.plantBased, false);
});

test("a goal under one gram reachable suggests 0", () => {
  assert.equal(
    goalWarning([plan("Clark", "short", 0.4)], 10, [])?.suggested,
    0,
  );
});
