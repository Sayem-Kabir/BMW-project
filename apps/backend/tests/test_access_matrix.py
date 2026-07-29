"""Role → feature matrix smoke tests (keep in sync with frontend access.ts)."""

from __future__ import annotations

from app.core.access import (
    FEATURE_ASSISTANT,
    FEATURE_DEMO,
    FEATURE_HOME_ADMIN,
    FEATURE_HOME_DRIVER,
    FEATURE_HOME_FLEET,
    FEATURE_MAINTENANCE,
    FEATURE_MONITOR,
    FEATURE_ROAD,
    FEATURE_SAFETY,
    FEATURE_ROLES,
    roles_for_feature,
)
from app.core.security import (
    ROLE_DRIVER,
    ROLE_FLEET_MANAGER,
    ROLE_MAINTENANCE_TECH,
    ROLE_ORG_ADMIN,
    ROLE_SUPER_ADMIN,
    normalize_role,
)


def test_matrix_driver_capabilities():
    assert ROLE_DRIVER in FEATURE_ROLES[FEATURE_HOME_DRIVER]
    assert ROLE_DRIVER not in FEATURE_ROLES[FEATURE_HOME_FLEET]
    assert ROLE_DRIVER not in FEATURE_ROLES[FEATURE_DEMO]
    assert ROLE_DRIVER not in FEATURE_ROLES[FEATURE_MAINTENANCE]
    assert ROLE_DRIVER in FEATURE_ROLES[FEATURE_MONITOR]
    assert ROLE_DRIVER in FEATURE_ROLES[FEATURE_SAFETY]
    assert ROLE_DRIVER in FEATURE_ROLES[FEATURE_ASSISTANT]


def test_matrix_maintenance_tech():
    assert ROLE_MAINTENANCE_TECH in FEATURE_ROLES[FEATURE_HOME_FLEET]
    assert ROLE_MAINTENANCE_TECH in FEATURE_ROLES[FEATURE_MAINTENANCE]
    assert ROLE_MAINTENANCE_TECH not in FEATURE_ROLES[FEATURE_DEMO]
    assert ROLE_MAINTENANCE_TECH not in FEATURE_ROLES[FEATURE_MONITOR]


def test_matrix_fleet_manager():
    assert ROLE_FLEET_MANAGER in FEATURE_ROLES[FEATURE_HOME_FLEET]
    assert ROLE_FLEET_MANAGER in FEATURE_ROLES[FEATURE_DEMO]
    assert ROLE_FLEET_MANAGER not in FEATURE_ROLES[FEATURE_HOME_ADMIN]


def test_matrix_admins():
    for role in (ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN):
        assert role in FEATURE_ROLES[FEATURE_HOME_ADMIN]
        assert role in FEATURE_ROLES[FEATURE_HOME_FLEET]
        assert role in FEATURE_ROLES[FEATURE_DEMO]
        assert role not in FEATURE_ROLES[FEATURE_MONITOR]
        assert role not in FEATURE_ROLES[FEATURE_ROAD]


def test_roles_for_feature_sorted():
    roles = roles_for_feature(FEATURE_DEMO)
    assert ROLE_FLEET_MANAGER in roles
    assert normalize_role("operator") == ROLE_FLEET_MANAGER
