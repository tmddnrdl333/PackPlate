"use client";

import type { Map as LeafletMap, Marker } from "leaflet";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { sortByDistance, walkingEstimate } from "@/lib/campusDistance";
import type { LocationSummary } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";
import { StatusPill } from "./Badges";
import { DistanceSort, useDistanceSort } from "./DistanceSort";
import { StateMessage } from "./StateMessage";

function statusText(isOpen: boolean | null) {
  if (isOpen === true) return "Open now";
  if (isOpen === false) return "Closed";
  return "Hours unknown";
}

function MapResults({ locations }: { locations: LocationSummary[] }) {
  const container = useRef<HTMLDivElement>(null);
  const markers = useRef(new Map<number, Marker>());
  const [mapState, setMapState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [tilesUnavailable, setTilesUnavailable] = useState(false);
  const controls = useDistanceSort(locations);
  const sorted = sortByDistance(
    locations,
    (location) => location.id,
    controls.distances,
  );
  const hasCoordinates = locations.some((location) => location.coordinates);

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    let cancelled = false;
    let map: LeafletMap | undefined;
    const markersById = markers.current;

    void import("leaflet")
      .then((L) => {
        if (cancelled) return;
        map = L.map(element, { scrollWheelZoom: false });
        const bounds = L.latLngBounds([]);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        })
          .on("tileerror", () => setTilesUnavailable(true))
          .addTo(map);

        for (const location of locations) {
          const point = location.coordinates;
          if (!point) continue;
          const latLng = L.latLng(point.latitude, point.longitude);
          const label = `${location.name} · ${statusText(location.is_open)}`;
          const tone =
            location.is_open === null
              ? "unknown"
              : location.is_open
                ? "open"
                : "closed";
          const marker = L.marker(latLng, {
            title: label,
            icon: L.divIcon({
              className: `campus-pin campus-pin-${tone}`,
              iconSize: [18, 18],
            }),
          }).addTo(map);
          marker.getElement()?.setAttribute("aria-label", label);
          const popup = document.createElement("div");
          const text = document.createElement("p");
          text.textContent = label;
          const link = document.createElement("a");
          link.href = `/menus?location=${location.id}`;
          link.textContent = "View menu";
          popup.append(text, link);
          marker.bindPopup(popup);
          markersById.set(location.id, marker);
          bounds.extend(latLng);
        }

        map.fitBounds(bounds, { padding: [24, 24], maxZoom: 17 });
        setMapState("ready");
      })
      .catch(() => {
        if (!cancelled) {
          map?.remove();
          map = undefined;
          markersById.clear();
          setMapState("error");
        }
      });

    return () => {
      cancelled = true;
      map?.remove();
      markersById.clear();
    };
  }, [locations]);

  return (
    <>
      <DistanceSort controls={controls} />
      {hasCoordinates && mapState !== "error" ? (
        <>
          <div
            ref={container}
            className="campus-map"
            role="region"
            aria-label="Dining locations map"
          />
          <p className="help">
            Green pins are open, red pins are closed, and amber pins have
            unknown hours.
          </p>
          {tilesUnavailable ? (
            <p className="help">
              Some map tiles couldn’t load. Dining locations are still listed
              below.
            </p>
          ) : null}
        </>
      ) : (
        <p className="help">
          {hasCoordinates
            ? "The map couldn’t load."
            : "No map coordinates are available yet."}
        </p>
      )}
      <ul className="stack" aria-label="Dining locations">
        {sorted.map((location) => {
          const meters = controls.distances.get(location.id);
          return (
            <li key={location.id} className="panel location-row">
              <div className="location-row-head">
                <span className="location-name">{location.name}</span>
                <StatusPill isOpen={location.is_open} />
              </div>
              {meters !== undefined ? (
                <p className="meta">{walkingEstimate(meters)}</p>
              ) : null}
              {!location.coordinates ? (
                <p className="meta">Map coordinates unavailable</p>
              ) : null}
              <div className="row-links">
                <Link href={`/menus?location=${location.id}`}>View menu</Link>
                {location.coordinates && mapState === "ready" ? (
                  <button
                    type="button"
                    className="btn btn-quiet btn-small"
                    aria-label={`Show ${location.name} on map`}
                    onClick={() => {
                      markers.current.get(location.id)?.openPopup();
                      container.current?.scrollIntoView({ block: "nearest" });
                    }}
                  >
                    Show on map
                  </button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}

export function CampusMap() {
  const { data, error, reload } = useAsync(api.locations, "campus-map");
  if (error)
    return (
      <StateMessage kind="error" onRetry={reload}>
        {error}
      </StateMessage>
    );
  if (!data)
    return <StateMessage kind="loading">Loading locations…</StateMessage>;
  if (!data.length)
    return (
      <StateMessage kind="empty">
        No dining locations have been loaded yet.
      </StateMessage>
    );
  return <MapResults locations={data} />;
}
