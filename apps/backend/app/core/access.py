"""Role → feature capability matrix.

Keep in sync with apps/frontend/src/lib/access.ts
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends

from app.core.security import (
    ROLE_DRIVER,
    ROLE_FLEET_MANAGER,
    ROLE_MAINTENANCE_TECH,
    ROLE_ORG_ADMIN,
    ROLE_SUPER_ADMIN,
    require_roles,
    require_user,
)
from app.models.user import User

# Feature IDs mirror the frontend FeatureId union
FEATURE_HOME_DRIVER = "home.driver"
FEATURE_HOME_FLEET = "home.fleet"
FEATURE_HOME_ADMIN = "home.admin"
FEATURE_DEMO = "demo"
FEATURE_MONITOR = "monitor"
FEATURE_ROAD = "road"
FEATURE_MAINTENANCE = "maintenance"
FEATURE_SAFETY = "safety"
FEATURE_ASSISTANT = "assistant"
FEATURE_API_DOCS = "api_docs"

FEATURE_ROLES: dict[str, frozenset[str]] = {
    FEATURE_HOME_DRIVER: frozenset({ROLE_DRIVER}),
    FEATURE_HOME_FLEET: frozenset(
        {
            ROLE_MAINTENANCE_TECH,
            ROLE_FLEET_MANAGER,
            ROLE_ORG_ADMIN,
            ROLE_SUPER_ADMIN,
        }
    ),
    FEATURE_HOME_ADMIN: frozenset({ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN}),
    FEATURE_DEMO: frozenset(
        {ROLE_FLEET_MANAGER, ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN}
    ),
    FEATURE_MONITOR: frozenset({ROLE_DRIVER, ROLE_FLEET_MANAGER}),
    FEATURE_ROAD: frozenset({ROLE_DRIVER, ROLE_FLEET_MANAGER}),
    FEATURE_MAINTENANCE: frozenset(
        {
            ROLE_MAINTENANCE_TECH,
            ROLE_FLEET_MANAGER,
            ROLE_ORG_ADMIN,
            ROLE_SUPER_ADMIN,
        }
    ),
    FEATURE_SAFETY: frozenset(
        {
            ROLE_DRIVER,
            ROLE_FLEET_MANAGER,
            ROLE_ORG_ADMIN,
            ROLE_SUPER_ADMIN,
        }
    ),
    FEATURE_ASSISTANT: frozenset(
        {
            ROLE_DRIVER,
            ROLE_MAINTENANCE_TECH,
            ROLE_FLEET_MANAGER,
            ROLE_ORG_ADMIN,
            ROLE_SUPER_ADMIN,
        }
    ),
    FEATURE_API_DOCS: frozenset({ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN}),
}


def roles_for_feature(feature: str) -> tuple[str, ...]:
    roles = FEATURE_ROLES.get(feature)
    if not roles:
        raise KeyError(f"Unknown feature: {feature}")
    return tuple(sorted(roles))


def require_feature(feature: str) -> Callable:
    """FastAPI dependency: user must have the given feature capability."""
    return require_roles(*roles_for_feature(feature))


async def require_authenticated(user: User = Depends(require_user)) -> User:
    """Any logged-in user (assistant and similar)."""
    return user
