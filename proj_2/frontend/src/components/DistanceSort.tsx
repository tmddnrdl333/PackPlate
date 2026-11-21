"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { distancesFrom, type Coordinates } from "@/lib/campusDistance";
import type { LocationSummary } from "@/lib/types";

type Position =
  | { status: "idle" | "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; origin: Coordinates; locations: LocationSummary[] };

export function useDistanceSort(locations?: LocationSummary[]) {
  const [position, setPosition] = useState<Position>({ status: "idle" });
  const origin = position.status === "ready" ? position.origin : null;
  const distances = distancesFrom(
    origin,
    locations ?? (position.status === "ready" ? position.locations : []),
  );

  function locate() {
    if (!navigator.geolocation) {
      setPosition({
        status: "error",
        message: "Location access is unavailable.",
      });
      return;
    }
    setPosition({ status: "loading" });
    navigator.geolocation.getCurrentPosition(
      async ({ coords: { latitude, longitude } }) => {
        try {
          setPosition({
            status: "ready",
            origin: { latitude, longitude },
            locations: locations ?? (await api.locations()),
          });
        } catch {
          setPosition({
            status: "error",
            message: "Couldn’t load dining locations for distance sorting.",
          });
        }
      },
      (error) => {
        setPosition({
          status: "error",
          message:
            error.code === 1
              ? "Location access was denied. Showing the default order."
              : "Couldn’t get your location. Showing the default order.",
        });
      },
      { timeout: 10_000, maximumAge: 60_000 },
    );
  }

  return {
    distances,
    position,
    locate,
    reset: () => setPosition({ status: "idle" }),
  };
}

export function DistanceSort({
  controls,
}: {
  controls: ReturnType<typeof useDistanceSort>;
}) {
  const { position, locate, reset, distances } = controls;
  const ready = position.status === "ready";
  return (
    <div>
      <button
        type="button"
        className="btn btn-outline"
        disabled={position.status === "loading"}
        onClick={ready ? reset : locate}
      >
        {ready
          ? "Restore default order"
          : position.status === "loading"
            ? "Getting location…"
            : "Sort by walking distance"}
      </button>
      <p className="help" role="status">
        {position.status === "error"
          ? position.message
          : ready && distances.size === 0
            ? "No dining coordinates are available. Showing the default order."
            : "Walking times estimate straight-line distance at 80 m/min."}
      </p>
    </div>
  );
}
