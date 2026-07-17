"""API v1 route package — routers are registered in app.main."""

from app.api.v1 import (
    analytics,
    assistant,
    auth,
    driver,
    events,
    fleet,
    maintenance,
    risk,
    road,
    telemetry,
    ws,
    xai,
)

ALL_ROUTERS = [
    auth.router,
    driver.router,
    road.router,
    risk.router,
    maintenance.router,
    assistant.router,
    fleet.router,
    events.router,
    analytics.router,
    xai.router,
    telemetry.router,
    ws.router,
]
