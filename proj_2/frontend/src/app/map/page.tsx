import "leaflet/dist/leaflet.css";
import "./campusMap.css";
import { CampusMap } from "@/components/CampusMap";
import { PageShell } from "@/components/PageShell";

export default function CampusMapPage() {
  return (
    <PageShell
      title="Campus Dining Map"
      lede="See what’s open and find dining locations near you."
    >
      <CampusMap />
    </PageShell>
  );
}
