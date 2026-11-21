"""Curated campus dining coordinates (Project 3 M3)."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# NetNutrition unit IDs, as used by ingestion/normalize.py. Coordinates are
# approximate points from NC State Dining's location pages or the host building.
# Talley venues share the building point. University Towers, Hunt Library, and
# the Textiles Complex use OpenStreetMap building locations. Jordan Hall and
# Park Shops use coordinates published by NC State Libraries and the calendar.
_COORDINATES = [
    (1, 35.7854786, -78.6776514),  # Fountain
    (2, 35.7828122, -78.6671769),  # Clark
    (3, 35.7828286, -78.6695785),  # Case
    (4, 35.78835, -78.67536),  # University Towers
    (5, 35.784007, -78.6708101),  # One Earth
    (6, 35.7702283, -78.6744475),  # On the Oval
    (7, 35.7876119, -78.6699832),  # Brickyard Pizza
    (8, 35.7875615, -78.6697106),  # Smoothie U
    (9, 35.784007, -78.6708101),  # Tuffy's
    (10, 35.784007, -78.6708101),  # Los Lobos
    (11, 35.784007, -78.6708101),  # Jason's Deli
    (12, 35.784007, -78.6708101),  # 1887 Bistro
    (13, 35.784007, -78.6708101),  # Talley Starbucks
    (14, 35.7876119, -78.6699832),  # Hill of Beans
    (15, 35.7692962, -78.6764433),  # Common Grounds
    (16, 35.7968693, -78.7040386),  # Creature Comforts
    (17, 35.771947, -78.6738541),  # Port City Java, Koch Hall
    (18, 35.784007, -78.6708101),  # Port City Java, Talley
    (19, 35.781636, -78.675894),  # Elements
    (20, 35.77034, -78.6788),  # Social Fabric
    (21, 35.7883579, -78.6739635),  # The Exchange
    (22, 35.785532, -78.66709),  # La Farm
    (23, 35.7986235, -78.7039576),  # Wolves' Den
    (24, 35.7600764, -78.677203),  # The Terrace
]


def upgrade():
    # This catalog can be installed on an empty database before the first scrape.
    table = op.create_table(
        "location_coordinates",
        sa.Column("location_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_longitude"),
    )
    op.bulk_insert(
        table,
        [
            {"location_id": unit_id, "latitude": latitude, "longitude": longitude}
            for unit_id, latitude, longitude in _COORDINATES
        ],
    )


def downgrade():
    op.drop_table("location_coordinates")
