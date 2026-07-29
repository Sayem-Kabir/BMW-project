"""Seed multi-vehicle demo fleet for Phase 4/6 safety + dashboard APIs.

Usage:

    python scripts/seed_safety_demo.py

Ids match the Safety UI, fleet dashboard, and demo_safety_phase4.py.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from sqlalchemy import create_engine, text

from app.core.config import settings

ORG_ID = uuid.UUID("00000000-0000-4000-8000-000000000010")
DRIVER_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
SESSION_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
VEHICLE_ID = uuid.UUID("00000000-0000-4000-8000-000000000003")

DRIVER_B = uuid.UUID("00000000-0000-4000-8000-000000000006")
DRIVER_C = uuid.UUID("00000000-0000-4000-8000-000000000007")
VEHICLE_B = uuid.UUID("00000000-0000-4000-8000-000000000004")
VEHICLE_C = uuid.UUID("00000000-0000-4000-8000-000000000005")
SESSION_B = uuid.UUID("00000000-0000-4000-8000-000000000008")
SESSION_C = uuid.UUID("00000000-0000-4000-8000-000000000009")


def _upsert_org(conn) -> None:
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


def _upsert_driver(conn, *, driver_id, name, email) -> None:
    conn.execute(
        text(
            """
            INSERT INTO drivers (id, name, email, org_id)
            VALUES (:id, :name, :email, :org_id)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": driver_id, "name": name, "email": email, "org_id": ORG_ID},
    )


def _upsert_vehicle(conn, *, vehicle_id, name, vin, model, year) -> None:
    conn.execute(
        text(
            """
            INSERT INTO vehicles (id, name, vin, model, year, org_id, is_active)
            VALUES (:id, :name, :vin, :model, :year, :org_id, true)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                vin = EXCLUDED.vin,
                model = EXCLUDED.model,
                year = EXCLUDED.year,
                org_id = EXCLUDED.org_id,
                is_active = true
            """
        ),
        {
            "id": vehicle_id,
            "name": name,
            "vin": vin,
            "model": model,
            "year": year,
            "org_id": ORG_ID,
        },
    )


def _upsert_session(conn, *, session_id, vehicle_id, driver_id) -> None:
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
        {"id": session_id, "vehicle_id": vehicle_id, "driver_id": driver_id},
    )


def _seed_scores(conn) -> None:
    today = date.today()
    rows = [
        (today - timedelta(days=i), DRIVER_ID, 92 - i, 1, 0, 0, 0, 0, 0)
        for i in range(7)
    ] + [
        (today - timedelta(days=i), DRIVER_B, 78 - i, 2, 1, 1, 1, 0, 0)
        for i in range(7)
    ] + [
        (today - timedelta(days=i), DRIVER_C, 64 - i * 2, 3, 2, 2, 2, 1, 1)
        for i in range(7)
    ]
    for day, driver_id, score, harsh, accel, speed, drowsy, phone, seatbelt in rows:
        conn.execute(
            text(
                """
                INSERT INTO driver_scores (
                    date, driver_id, safety_score,
                    harsh_braking_count, rapid_acceleration_count, speeding_events,
                    drowsiness_events, phone_usage_events, no_seatbelt_events,
                    total_distance_km, total_drive_time_minutes
                )
                VALUES (
                    :date, :driver_id, :safety_score,
                    :harsh, :accel, :speed,
                    :drowsy, :phone, :seatbelt,
                    :distance, :minutes
                )
                ON CONFLICT (date, driver_id) DO UPDATE SET
                    safety_score = EXCLUDED.safety_score
                """
            ),
            {
                "date": day,
                "driver_id": driver_id,
                "safety_score": score,
                "harsh": harsh,
                "accel": accel,
                "speed": speed,
                "drowsy": drowsy,
                "phone": phone,
                "seatbelt": seatbelt,
                "distance": 40.0 + score / 10.0,
                "minutes": 60 + score,
            },
        )


def _seed_risk(conn) -> None:
    now = datetime.now(timezone.utc)
    samples = [
        (VEHICLE_ID, 22.0, "LOW"),
        (VEHICLE_B, 58.0, "MEDIUM"),
        (VEHICLE_C, 81.0, "HIGH"),
    ]
    for vehicle_id, score, level in samples:
        conn.execute(
            text(
                """
                INSERT INTO risk_scores (id, vehicle_id, score, level, payload, timestamp)
                VALUES (:id, :vehicle_id, :score, :level, CAST(:payload AS jsonb), :timestamp)
                """
            ),
            {
                "id": uuid.uuid4(),
                "vehicle_id": vehicle_id,
                "score": score,
                "level": level,
                "payload": (
                    f'{{"vehicle_id":"{vehicle_id}","score":{score},'
                    f'"level":"{level}","risk_score":{score},"risk_level":"{level}",'
                    f'"reasons":["seeded demo risk"],"phase":"6A"}}'
                ),
                "timestamp": now,
            },
        )


USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000011")
VIEWER_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000012")
ORG_ADMIN_ID = uuid.UUID("00000000-0000-4000-8000-000000000013")
DRIVER_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000014")
MAINT_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000015")
SUPER_ADMIN_ID = uuid.UUID("00000000-0000-4000-8000-000000000016")
DEMO_USER_EMAIL = "demo@bmwai.dev"
DEMO_USER_PASSWORD = "demo1234"
VIEWER_USER_EMAIL = "viewer@bmwai.dev"
VIEWER_USER_PASSWORD = "viewer1234"


def _upsert_role_user(
    conn,
    *,
    user_id: uuid.UUID,
    email: str,
    password: str,
    full_name: str,
    role: str,
    driver_id: uuid.UUID | None = None,
) -> None:
    from app.core.security import get_password_hash

    hashed = get_password_hash(password)
    # Upsert by email (unique) so re-seeds always reset password/role even if IDs differ
    conn.execute(
        text(
            """
            INSERT INTO users (
                id, email, hashed_password, full_name, role, org_id,
                is_active, is_email_verified, mfa_enabled, driver_id
            )
            VALUES (
                :id, :email, :hashed_password, :full_name, :role, :org_id,
                true, true, false, :driver_id
            )
            ON CONFLICT (email) DO UPDATE SET
                hashed_password = EXCLUDED.hashed_password,
                full_name = EXCLUDED.full_name,
                role = EXCLUDED.role,
                org_id = EXCLUDED.org_id,
                is_email_verified = true,
                is_active = true,
                mfa_enabled = false,
                driver_id = COALESCE(EXCLUDED.driver_id, users.driver_id)
            """
        ),
        {
            "id": user_id,
            "email": email,
            "hashed_password": hashed,
            "full_name": full_name,
            "role": role,
            "org_id": ORG_ID,
            "driver_id": driver_id,
        },
    )


def _upsert_user(conn) -> None:
    # Spec Phase 8C — five roles (+ legacy viewer mapped as driver-like read demo)
    _upsert_role_user(
        conn,
        user_id=USER_ID,
        email=DEMO_USER_EMAIL,
        password=DEMO_USER_PASSWORD,
        full_name="Demo Fleet Manager",
        role="fleet_manager",
    )
    _upsert_role_user(
        conn,
        user_id=ORG_ADMIN_ID,
        email="admin@bmwai.dev",
        password="admin1234",
        full_name="Demo Org Admin",
        role="org_admin",
    )
    _upsert_role_user(
        conn,
        user_id=DRIVER_USER_ID,
        email="driver@bmwai.dev",
        password="driver1234",
        full_name="Demo Driver User",
        role="driver",
        driver_id=DRIVER_ID,
    )
    _upsert_role_user(
        conn,
        user_id=MAINT_USER_ID,
        email="tech@bmwai.dev",
        password="tech1234",
        full_name="Demo Maintenance Tech",
        role="maintenance_tech",
    )
    _upsert_role_user(
        conn,
        user_id=SUPER_ADMIN_ID,
        email="super@bmwai.dev",
        password="super1234",
        full_name="Demo Super Admin",
        role="super_admin",
    )
    _upsert_role_user(
        conn,
        user_id=VIEWER_USER_ID,
        email=VIEWER_USER_EMAIL,
        password=VIEWER_USER_PASSWORD,
        full_name="Demo Viewer (legacy)",
        role="viewer",
    )
    # Link driver row to login user (ignore if column not yet migrated)
    try:
        # SAVEPOINT so a missing column does not abort the whole seed transaction
        conn.execute(text("SAVEPOINT sp_driver_link"))
        conn.execute(
            text("UPDATE drivers SET user_id = :uid WHERE id = :did"),
            {"uid": DRIVER_USER_ID, "did": DRIVER_ID},
        )
        conn.execute(text("RELEASE SAVEPOINT sp_driver_link"))
    except Exception as exc:  # noqa: BLE001
        conn.execute(text("ROLLBACK TO SAVEPOINT sp_driver_link"))
        print(f"driver.user_id link skipped: {exc}")


def main() -> int:
    engine = create_engine(settings.database_url_sync)

    with engine.begin() as conn:
        _upsert_org(conn)
        _upsert_driver(
            conn,
            driver_id=DRIVER_ID,
            name="Demo Driver",
            email="demo.driver@bmwai.local",
        )
        _upsert_driver(
            conn,
            driver_id=DRIVER_B,
            name="Alex Rivera",
            email="alex.rivera@bmwai.local",
        )
        _upsert_driver(
            conn,
            driver_id=DRIVER_C,
            name="Sam Chen",
            email="sam.chen@bmwai.local",
        )
        _upsert_vehicle(
            conn,
            vehicle_id=VEHICLE_ID,
            name="Demo BMW i4",
            vin="WBADEMO0000000003",
            model="i4",
            year=2024,
        )
        _upsert_vehicle(
            conn,
            vehicle_id=VEHICLE_B,
            name="Demo BMW X5",
            vin="WBADEMO0000000004",
            model="X5",
            year=2023,
        )
        _upsert_vehicle(
            conn,
            vehicle_id=VEHICLE_C,
            name="Demo BMW iX",
            vin="WBADEMO0000000005",
            model="iX",
            year=2024,
        )
        _upsert_session(conn, session_id=SESSION_ID, vehicle_id=VEHICLE_ID, driver_id=DRIVER_ID)
        _upsert_session(conn, session_id=SESSION_B, vehicle_id=VEHICLE_B, driver_id=DRIVER_B)
        _upsert_session(conn, session_id=SESSION_C, vehicle_id=VEHICLE_C, driver_id=DRIVER_C)
        try:
            _seed_scores(conn)
        except Exception as exc:  # noqa: BLE001
            print(f"driver_scores seed skipped: {exc}")
        try:
            _seed_risk(conn)
        except Exception as exc:  # noqa: BLE001
            print(f"risk_scores seed skipped: {exc}")
        try:
            _upsert_user(conn)
        except Exception as exc:  # noqa: BLE001
            print(f"demo user seed skipped: {exc}")

    print("Seeded safety/fleet demo data:")
    print(f"  org      {ORG_ID}")
    print(f"  drivers  {DRIVER_ID}, {DRIVER_B}, {DRIVER_C}")
    print(f"  vehicles {VEHICLE_ID}, {VEHICLE_B}, {VEHICLE_C}")
    print(f"  user     {DEMO_USER_EMAIL} / {DEMO_USER_PASSWORD} (fleet_manager)")
    print("  admin    admin@bmwai.dev / admin1234 (org_admin)")
    print("  driver   driver@bmwai.dev / driver1234 (driver)")
    print("  tech     tech@bmwai.dev / tech1234 (maintenance_tech)")
    print("  super    super@bmwai.dev / super1234 (super_admin)")
    print(f"  viewer   {VIEWER_USER_EMAIL} / {VIEWER_USER_PASSWORD} (legacy viewer)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
