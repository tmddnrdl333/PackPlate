"use client";

// Plan My Day (Project 3, M2). Allergies and diets start from the saved
// profile (My diet); the daily goals live only on this page.
import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";
import { api, errorMessage } from "@/lib/api";
import { sortByDistance, walkingEstimate } from "@/lib/campusDistance";
import { ALLERGENS, DIETS } from "@/lib/diet";
import { formatNumber } from "@/lib/format";
import {
  PLAN_DEFAULTS,
  PLAN_LIMITS,
  goalWarning,
  progress,
  validatePlan,
  type LocationPlan,
  type PlanRequest,
} from "@/lib/planner";
import { useHydrated, useSavedProfile } from "@/lib/profileStore";
import { stationLabel } from "@/lib/stations";
import type { Allergen, Diet, Profile } from "@/lib/types";
import { VerdictBadge } from "./Badges";
import { DistanceSort, useDistanceSort } from "./DistanceSort";
import { StateMessage } from "./StateMessage";

type Search =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "done"; plans: LocationPlan[]; goal: number };

const SHOWN = 3; // plans shown in full; the rest are listed by name

function toggle<T>(list: T[], key: T): T[] {
  return list.includes(key) ? list.filter((k) => k !== key) : [...list, key];
}

function PlanCard({
  plan,
  goal,
  meters,
}: {
  plan: LocationPlan;
  goal: number;
  meters: number | undefined;
}) {
  const met = plan.status === "met";
  return (
    <li
      className={`panel result-card ${met ? "result-everyone" : "result-left-out"}`}
    >
      <div className="location-row-head">
        <span className="location-name">{plan.location_name}</span>
        <span className={met ? "pill pill-ok" : "pill pill-warn"}>
          {met ? "✓ Goal met" : `${progress(plan, goal)}% of goal`}
        </span>
      </div>
      <p className="meta">
        {formatNumber(plan.protein_g, " g")} protein ·{" "}
        {formatNumber(plan.calories, " cal")} · {plan.items.length} dish
        {plan.items.length === 1 ? "" : "es"} · chosen from {plan.candidates}{" "}
        that fit you
      </p>
      {meters !== undefined ? (
        <p className="meta">{walkingEstimate(meters)}</p>
      ) : null}
      {/* The shared table style is sized for one label; a plan needs the full width. */}
      <table className="nutrition-table" style={{ maxWidth: "none" }}>
        <caption className="visually-hidden">
          Planned dishes at {plan.location_name}
        </caption>
        <thead>
          <tr>
            <th scope="col">Dish</th>
            <th scope="col">Meal</th>
            <th scope="col">Protein</th>
            <th scope="col">Calories</th>
            <th scope="col">For you</th>
          </tr>
        </thead>
        <tbody>
          {plan.items.map((item) => (
            <tr key={item.id}>
              <td style={{ textAlign: "left" }}>
                {item.name}
                {item.course ? (
                  <span className="help"> · {stationLabel(item.course)}</span>
                ) : null}
              </td>
              <td style={{ textAlign: "left" }}>{item.meal}</td>
              <td>{formatNumber(item.nutrition?.protein_g ?? null, " g")}</td>
              <td>{formatNumber(item.nutrition?.calories ?? null, "")}</td>
              <td>
                <VerdictBadge verdict="fits" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="row-links">
        <Link href={`/menus?location=${plan.location_id}`}>View menu</Link>
      </div>
    </li>
  );
}

function PlannerForm({ saved }: { saved: Profile }) {
  const [avoid, setAvoid] = useState<Allergen[]>(saved.avoid);
  const [diets, setDiets] = useState<Diet[]>(saved.diets);
  const [protein, setProtein] = useState<string>(
    String(PLAN_DEFAULTS.protein_goal_g),
  );
  const [calories, setCalories] = useState<string>(
    String(PLAN_DEFAULTS.max_calories),
  );
  const [maxItems, setMaxItems] = useState<string>(
    String(PLAN_DEFAULTS.max_items),
  );
  const [date, setDate] = useState<string>("");
  const [problem, setProblem] = useState<string | null>(null);
  const [search, setSearch] = useState<Search>({ status: "idle" });
  const distance = useDistanceSort();
  // Bumped on every edit and every submit. A plan is only shown if nothing
  // changed since it was asked for, so it can never be read as the plan for
  // allergies or goals the student has since changed.
  const requestId = useRef(0);

  function edited() {
    requestId.current += 1;
    setSearch({ status: "idle" });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body: PlanRequest = {
      avoid,
      diets,
      protein_goal_g: Number(protein),
      max_calories: Number(calories),
      max_items: Number(maxItems),
    };
    const invalid = validatePlan(body);
    if (invalid) {
      setProblem(invalid);
      return;
    }
    setProblem(null);
    const id = ++requestId.current;
    setSearch({ status: "loading" });
    try {
      const plans = await api.planDay(body, date || undefined);
      if (id !== requestId.current) return; // inputs changed meanwhile
      setSearch({ status: "done", plans, goal: body.protein_goal_g });
    } catch (error) {
      if (id !== requestId.current) return;
      setSearch({ status: "error", message: errorMessage(error) });
    }
  }

  const done = search.status === "done" ? search : null;
  const met = done?.plans.filter((p) => p.status === "met") ?? [];
  const short = done?.plans.filter((p) => p.status === "short") ?? [];
  const best = sortByDistance(
    met.length > 0 ? met : short,
    (plan) => plan.location_id,
    distance.distances,
  );
  const warning = done ? goalWarning(done.plans, done.goal, diets) : null;
  const noMenus =
    done !== null && done.plans.every((p) => p.items_checked === 0);
  const someFit = done?.plans.some((p) => p.candidates > 0) ?? false;

  return (
    <>
      <form className="panel form" onSubmit={onSubmit}>
        <fieldset>
          <legend>Allergies: avoid these</legend>
          <div className="chips">
            {ALLERGENS.map((allergen) => (
              <label key={allergen.key} className="chip">
                <input
                  type="checkbox"
                  checked={avoid.includes(allergen.key)}
                  onChange={() => {
                    setAvoid((list) => toggle(list, allergen.key));
                    edited();
                  }}
                />
                <span>{allergen.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>Dietary preferences</legend>
          <div className="chips">
            {DIETS.map((diet) => (
              <label key={diet.key} className="chip">
                <input
                  type="checkbox"
                  checked={diets.includes(diet.key)}
                  onChange={() => {
                    setDiets((list) => toggle(list, diet.key));
                    edited();
                  }}
                />
                <span>{diet.label}</span>
              </label>
            ))}
          </div>
          <p className="help">
            Filled in from My diet. Changes here are not saved.
          </p>
        </fieldset>

        <fieldset>
          <legend>Your day</legend>
          <div className="number-grid">
            <div className="field">
              <label htmlFor="plan-protein">Protein goal (g)</label>
              <input
                id="plan-protein"
                className="input"
                type="number"
                inputMode="decimal"
                min={0}
                step="any"
                max={PLAN_LIMITS.protein_goal_g}
                value={protein}
                onChange={(event) => {
                  setProtein(event.target.value);
                  edited();
                }}
              />
            </div>
            <div className="field">
              <label htmlFor="plan-calories">Calorie limit</label>
              <input
                id="plan-calories"
                className="input"
                type="number"
                inputMode="decimal"
                min={0}
                step="any"
                max={PLAN_LIMITS.max_calories}
                value={calories}
                onChange={(event) => {
                  setCalories(event.target.value);
                  edited();
                }}
              />
            </div>
            <div className="field">
              <label htmlFor="plan-items">Most dishes</label>
              <input
                id="plan-items"
                className="input"
                type="number"
                inputMode="numeric"
                min={1}
                max={PLAN_LIMITS.max_items}
                value={maxItems}
                onChange={(event) => {
                  setMaxItems(event.target.value);
                  edited();
                }}
              />
            </div>
            <div className="field">
              <label htmlFor="plan-date">Day (blank = today)</label>
              <input
                id="plan-date"
                className="input"
                type="date"
                value={date}
                onChange={(event) => {
                  setDate(event.target.value);
                  edited();
                }}
              />
            </div>
          </div>
          <p className="help">
            A plan uses one dining location, mixing its stations and meals. It
            only uses dishes that fit you and have a full nutrition label.
          </p>
        </fieldset>

        {problem ? (
          <p className="form-error" role="alert">
            {problem}
          </p>
        ) : null}

        <div className="button-row">
          <button
            type="submit"
            className="btn"
            disabled={search.status === "loading"}
          >
            {search.status === "loading" ? "Planning…" : "Plan my day"}
          </button>
        </div>
      </form>

      <section aria-live="polite" aria-label="Plans">
        {search.status === "error" ? (
          <StateMessage kind="error">{search.message}</StateMessage>
        ) : null}

        {done ? (
          best.length === 0 ? (
            <StateMessage kind="empty">
              {noMenus
                ? "No menus are loaded for this day yet. Try another day."
                : someFit
                  ? "Some dishes fit you, but none fits your calorie limit with any protein. Try a higher calorie limit."
                  : "No location has a dish that fits you with a full nutrition label on this day. Try another day, or remove a restriction."}
            </StateMessage>
          ) : (
            <div className="page-body" style={{ marginTop: 0 }}>
              <h2 className="section-title">
                {met.length > 0
                  ? "Plans that reach your goal"
                  : "Plans that fall short of your goal"}{" "}
                <span className="count">({best.length})</span>
              </h2>
              <DistanceSort controls={distance} />
              {warning ? (
                <div className="banner banner-warn" role="status">
                  <p style={{ margin: 0 }}>
                    <strong>
                      No dining location can reach{" "}
                      {formatNumber(warning.goal, " g")} of protein for you on
                      this day.
                    </strong>{" "}
                    The most any one location offers within your limits is{" "}
                    {formatNumber(warning.reachable, " g")} ({warning.location}
                    ).
                    {warning.plantBased
                      ? " Campus menus have few high-protein vegetarian and vegan dishes, so high goals are often out of reach at one location."
                      : ""}
                  </p>
                  {warning.suggested > 0 ? (
                    <div className="button-row" style={{ marginTop: 8 }}>
                      <button
                        type="button"
                        className="btn"
                        onClick={() => {
                          setProtein(String(warning.suggested));
                          edited();
                        }}
                      >
                        Use a {warning.suggested} g goal
                      </button>
                    </div>
                  ) : null}
                  <p className="help" style={{ marginBottom: 0 }}>
                    Or try a higher calorie limit or more dishes.
                  </p>
                </div>
              ) : null}
              <ul className="stack">
                {best.slice(0, SHOWN).map((plan) => (
                  <PlanCard
                    key={plan.location_id}
                    plan={plan}
                    goal={done.goal}
                    meters={distance.distances.get(plan.location_id)}
                  />
                ))}
              </ul>
              {best.length > SHOWN ? (
                <p className="help">
                  Also:{" "}
                  {best
                    .slice(SHOWN)
                    .map((p) => {
                      const meters = distance.distances.get(p.location_id);
                      const walk =
                        meters === undefined
                          ? ""
                          : `, ${walkingEstimate(meters)}`;
                      return `${p.location_name} (${formatNumber(p.protein_g, " g")}, ${formatNumber(p.calories, " cal")}${walk})`;
                    })
                    .join(" · ")}
                </p>
              ) : null}
              <p className="help">
                Labels come from NC State and can be wrong. If you have a
                serious allergy, check with dining staff.
              </p>
            </div>
          )
        ) : null}
      </section>
    </>
  );
}

export function MealPlanner() {
  const hydrated = useHydrated();
  const saved = useSavedProfile();
  if (!hydrated) return <StateMessage kind="loading">Loading…</StateMessage>;
  return <PlannerForm saved={saved} />;
}
