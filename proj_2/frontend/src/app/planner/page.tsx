import { MealPlanner } from "@/components/MealPlanner";
import { PageShell } from "@/components/PageShell";

// Plan My Day (Project 3, M2): dishes from one location that reach a daily
// protein goal under a calorie limit. Backed by POST /planner/day.
export default function PlannerPage() {
  return (
    <PageShell
      title="Plan My Day"
      lede="Set a protein goal and a calorie limit. PackPlate picks dishes from one dining location that get you there, using only dishes that fit your diet."
    >
      <MealPlanner />
    </PageShell>
  );
}
