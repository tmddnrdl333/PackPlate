from datetime import date

import pytest

from db.models import LocationCoordinate


@pytest.mark.parametrize("location_id", [1, 99])
def test_coordinates_in_location_list_and_detail(client, db, seed, location_id):
    seed.location(location_id)
    seed.menu(101, location_id, date(2026, 10, 6), "Lunch")
    seed.item(101, "Soup")

    expected = None
    if location_id == 1:
        expected = {"latitude": 35.7854786, "longitude": -78.6776514}
        db.add(LocationCoordinate(location_id=location_id, **expected))
        db.commit()

    [summary] = client.get("/locations").json()
    assert summary["coordinates"] == expected
    assert client.get(f"/locations/{location_id}").json()["coordinates"] == expected
