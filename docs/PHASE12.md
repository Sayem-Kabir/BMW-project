# Spec Phase 12 — Notifications & Product Polish

## Modules

| Module | Deliverable |
|--------|-------------|
| **12A** | CRITICAL alerts via Resend email + Twilio SMS (console fallback); prefs `GET/PATCH /api/v1/notifications/preferences`; webhooks `POST/GET /api/v1/notifications/webhooks`; fan-out on event detect; `POST .../test/critical` |
| **12B** | Driver PWA — `public/manifest.webmanifest`, `sw.js`, icons, SW register in root layout |
| **12C** | Skip link, ARIA nav, focus rings, CSS theme tokens + Light/Dark toggle in `RoleShell` |
| **12D** | `GET /api/v1/analytics/driver/{id}/weekly.pdf` — same data as weekly JSON |

## Exit criteria

1. CRITICAL safety event (or `/notifications/test/critical`) records an email send (console or Resend) within seconds.
2. Driver dashboard is installable (manifest + service worker).
3. Keyboard skip-to-content + theme toggle available on role shells.
4. Weekly PDF returns `application/pdf` with `%PDF` header.

## Quick demos

```bash
# Synthetic CRITICAL notify (admin JWT)
curl -X POST http://127.0.0.1:8001/api/v1/notifications/test/critical \
  -H "Authorization: Bearer $TOKEN"

# Preferences
curl http://127.0.0.1:8001/api/v1/notifications/preferences \
  -H "Authorization: Bearer $TOKEN"

# Weekly PDF
curl -OJ http://127.0.0.1:8001/api/v1/analytics/driver/$DRIVER_ID/weekly.pdf \
  -H "Authorization: Bearer $TOKEN"
```

## Migration

```bash
cd apps/backend
alembic upgrade head
# revision 005_notifications_12 — notification_preferences + notification_webhooks
```

## Env (optional)

See root `.env.example`: `RESEND_*`, `TWILIO_*`, `NOTIFY_CRITICAL_EMAIL_FALLBACK`.
Without keys, alerts log to console and `_SENT_LOG` (tests).
