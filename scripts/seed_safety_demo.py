"""Seed demo org, driver, and vehicle for Phase 4 safety APIs.

Usage:

    python scripts/seed_safety_demo.py

Ids match the Safety UI and demo_safety_phase4.py.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Repo root on path for apps.backend imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from sqlalchemy import create_engine, text

from app.core.config import settings

ORG_ID = uuid.UUID("00000000-0000-4000-8000-000000000010")
DRIVER_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
SESSION_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
VEHICLE_ID = uuid.UUID("00000000-0000-4000-8000-000000000003")


def main() -> int:
    engine = create_engine(settings.database_url_sync)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO organizations (id, name)
                VALUES (:id, :name)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": ORG_ID, "name": "Demo Fleet"},
        )
        conn.execute(
            text(
                """
                INSERT INTO drivers (id, name, email, org_id)
                VALUES (:id, :name, :email, :org_id)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": DRIVER_ID,
                "name": "Demo Driver",
                "email": "demo.driver@bmwai.local",
                "org_id": ORG_ID,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO vehicles (id, name, vin, model, year, org_id, is_active)
                VALUES (:id, :name, :vin, :model, :year, :org_id, true)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": VEHICLE_ID,
                "name": "Demo BMW i4",
                "vin": "WBADEMO0000000003",
                "model": "i4",
                "year": 2024,
                "org_id": ORG_ID,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO driver_sessions (
                    id, vehicle_id, driver_id, started_at,
                    drowsy_events, yawn_events, phone_events,
                    seatbelt_events, headpose_events, total_frames_analyzed
                )
                VALUES (
                    :id, :vehicle_id, :driver_id, NOW(),
                    0, 0, 0, 0, 0, 0
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": SESSION_ID,
                "vehicle_id": VEHICLE_ID,
                "driver_id": DRIVER_ID,
            },
        )

    print("Seeded safety demo data:")
    print(f"  org     {ORG_ID}")
    print(f"  driver  {DRIVER_ID}")
    print(f"  session {SESSION_ID}")
    print(f"  vehicle {VEHICLE_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
