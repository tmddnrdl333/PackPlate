import assert from "node:assert/strict";
import { test } from "node:test";
import {
  distanceMeters,
  distancesFrom,
  sortByDistance,
  walkingEstimate,
} from "../src/lib/campusDistance.ts";

const point = (latitude: number, longitude: number) => ({
  latitude,
  longitude,
});
const origin = point(0, 0);
const quarterCircumference = 10_007_543.398;

function near(actual: number, expected: number, tolerance = 0.01) {
  assert.ok(
    Math.abs(actual - expected) < tolerance,
    `Expected ${actual} to be within ${tolerance} of ${expected}`,
  );
}

for (const degrees of [0.001, 1, 30, 90, 179.9, 180]) {
  for (const [direction, destination] of [
    ["east", point(0, degrees)],
    ["west", point(0, -degrees)],
    ["north on a meridian", point(degrees - 90, 0)],
    ["south on a meridian", point(90 - degrees, 0)],
  ] as const) {
    test(`distance across ${degrees}° ${direction}`, () => {
      const start =
        direction === "north on a meridian"
          ? point(-90, 0)
          : direction === "south on a meridian"
            ? point(90, 0)
            : origin;
      near(
        distanceMeters(start, destination),
        (degrees / 90) * quarterCircumference,
      );
    });
  }
}

for (const [from, to, expected] of [
  [point(0, 179), point(0, -179), 222_389.853],
  [point(-90, 20), point(-90, -160), 0],
  [point(90, 90), point(90, -90), 0],
  [point(45, 0), point(45, 180), quarterCircumference],
  [point(-45, 0), point(-45, 180), quarterCircumference],
  [point(0, 90), point(90, 0), quarterCircumference],
  [point(35.7854786, -78.6776514), point(35.7828122, -78.6671769), 989.7],
] as const) {
  test(`great-circle distance ${from.latitude},${from.longitude} to ${to.latitude},${to.longitude}`, () => {
    near(distanceMeters(from, to), expected, 1);
    near(distanceMeters(to, from), expected, 1);
  });
}

for (const [meters, minutes] of [
  [0, 0],
  [0.01, 1],
  [79.99, 1],
  [80, 1],
  [80.01, 2],
  [159.99, 2],
  [160, 2],
  [160.01, 3],
  [240, 3],
  [240.01, 4],
  [320, 4],
  [1000, 13],
] as const) {
  test(`estimated walk for ${meters} m is ${minutes} minutes`, () => {
    assert.equal(walkingEstimate(meters), `~${minutes} min walk`);
  });
}

const locations = [
  { id: 50 },
  { id: 30, coordinates: point(0, 0.003) },
  { id: 20, coordinates: point(0, 0.002) },
  { id: 10, coordinates: origin },
  { id: 21, coordinates: point(0, -0.002) },
  { id: 51, coordinates: null },
];
const idOf = ({ id }: { id: number }) => id;

test("sorts by raw distance, with stable ties and missing coordinates last", () => {
  const sorted = sortByDistance(
    locations,
    idOf,
    distancesFrom(origin, locations),
  );
  assert.deepEqual(sorted.map(idOf), [10, 20, 21, 30, 50, 51]);
});

test("sorts distances that round to the same walking time", () => {
  const values = [{ id: 1 }, { id: 2 }];
  const distances = new Map([
    [1, 150],
    [2, 100],
  ]);
  assert.deepEqual(sortByDistance(values, idOf, distances).map(idOf), [2, 1]);
});

test("permission denial or unavailable position leaves the original order", () => {
  assert.deepEqual(
    sortByDistance(locations, idOf, distancesFrom(null, locations)),
    locations,
  );
});

test("a coordinate at the user's origin keeps a distance of zero", () => {
  assert.equal(distancesFrom(origin, locations).get(10), 0);
});

test("missing and null coordinates stay out of the distance lookup", () => {
  const distances = distancesFrom(origin, locations);
  assert.equal(distances.size, 4);
  assert.equal(distances.has(50), false);
  assert.equal(distances.has(51), false);
});

test("distance sorting leaves the input array intact", () => {
  sortByDistance(
    Object.freeze(locations),
    idOf,
    distancesFrom(origin, locations),
  );
  assert.deepEqual(locations.map(idOf), [50, 30, 20, 10, 21, 51]);
});

test("handles empty results", () => {
  assert.deepEqual(sortByDistance([], idOf, distancesFrom(origin, [])), []);
});
