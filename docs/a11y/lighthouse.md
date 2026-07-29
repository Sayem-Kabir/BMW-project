# Accessibility / Lighthouse — Spec Phase 12C exit criteria

Target: Lighthouse accessibility **≥ 90** on role shells.

## Manual checklist (already in UI)

- [x] Skip link (`#main-content`) in root layout
- [x] `aria-label` on primary nav (`RoleShell`)
- [x] Visible `:focus-visible` rings
- [x] Light/dark theme toggle with contrast tokens
- [x] Semantic `<main>` / `<header role="banner">`

## Measure

```bash
# With frontend on :3000
npx --yes lighthouse http://127.0.0.1:3000/login --only-categories=accessibility --quiet --chrome-flags="--headless"
npx --yes lighthouse http://127.0.0.1:3000/driver/dashboard --only-categories=accessibility --quiet --chrome-flags="--headless"
npx --yes lighthouse http://127.0.0.1:3000/fleet/dashboard --only-categories=accessibility --quiet --chrome-flags="--headless"
```

| Page | Score | Date | Notes |
|------|-------|------|-------|
| /login | _run locally_ | | |
| /driver/dashboard | | | login cookie required |
| /fleet/dashboard | | | |

## axe DevTools

Install axe browser extension → scan `/driver/dashboard` and `/fleet/dashboard` → zero critical issues.
