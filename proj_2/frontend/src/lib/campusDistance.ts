export interface Coordinates {
  latitude: number;
  longitude: number;
}

const EARTH_RADIUS_METERS = 6_371_000;
const WALKING_METERS_PER_MINUTE = 80;
const radians = (degrees: number) => (degrees * Math.PI) / 180;

export function distanceMeters(from: Coordinates, to: Coordinates): number {
  const fromLat = radians(from.latitude);
  const toLat = radians(to.latitude);
  const deltaLng = radians(to.longitude - from.longitude);
  const halfChord =
    Math.sin((toLat - fromLat) / 2) ** 2 +
    Math.cos(fromLat) * Math.cos(toLat) * Math.sin(deltaLng / 2) ** 2;
  return 2 * EARTH_RADIUS_METERS * Math.asin(Math.min(1, Math.sqrt(halfChord)));
}

export function walkingEstimate(meters: number): string {
  return `~${Math.ceil(meters / WALKING_METERS_PER_MINUTE)} min walk`;
}

export function distancesFrom(
  origin: Coordinates | null,
  locations: readonly { id: number; coordinates?: Coordinates | null }[],
): ReadonlyMap<number, number> {
  const distances = new Map<number, number>();
  if (origin) {
    for (const { id, coordinates } of locations) {
      if (coordinates) distances.set(id, distanceMeters(origin, coordinates));
    }
  }
  return distances;
}

export function sortByDistance<T>(
  values: readonly T[],
  idOf: (value: T) => number,
  distances: ReadonlyMap<number, number>,
): T[] {
  return [...values].sort((left, right) => {
    const a = distances.get(idOf(left));
    const b = distances.get(idOf(right));
    if (a === undefined) return b === undefined ? 0 : 1;
    if (b === undefined) return -1;
    return a - b;
  });
}
