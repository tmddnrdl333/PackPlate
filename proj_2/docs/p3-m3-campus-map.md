# M3 Campus Dining Map

Run the backend and frontend using the [local setup guide](../../INSTALL.md). Apply the latest Alembic migration from `proj_2` before starting the backend.

```sh
alembic -c db/alembic.ini upgrade head
```

Open **Campus map** in the site navigation. The map uses the dining locations already listed by PackPlate and their existing open, closed, or unknown hours. Select **Sort by walking distance** and allow location access to see the closest locations first. Each list entry has a menu link and, where coordinates are available, a button to open its pin. Locations in the same building can share a point.

Try the same sort on **Eat as a group** and **Plan my day** after generating results. Group matches and meal plan goal status still determine which results are shown together. If location access is denied or unavailable, the original order stays in place. Results without coordinates appear at the end when distance sorting is active.

Walking times round up from Haversine distance divided by 80 meters per minute. Coordinates stay in browser memory for the current page. The Leaflet basemap loads public OpenStreetMap tiles and the dining list remains usable when tiles fail.

Run `npm test` from `proj_2/frontend` for the distance tests. The backend suite covers coordinates in both the location list and detail responses.
