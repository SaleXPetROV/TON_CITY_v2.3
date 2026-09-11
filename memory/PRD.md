# TON CITY v2.3 — PRD / working notes

## Source
GitHub: https://github.com/SaleXPetROV/TON_CITY_v2.3.git (cloned into /app).
Stack: FastAPI (backend/server.py + routes/ + core/) + React (frontend) + MongoDB.
Telegram mini-app game "GRAM City". Bot NOT run locally (per user: web/logic testing only).

## Canonical preview URL
frontend/.env REACT_APP_BACKEND_URL = https://business-empire-48.preview.emergentagent.com
(Platform-managed / protected. It resets to this value on pod resume — do NOT rely on other hostnames.)

## Session: fixes 2026-06 (dates approximate to env clock)

### Task 1 — Admin «Кредиты → Изъятые» must list ONLY real seizures
Problem: every level-0 (leased) business was landing in the "Изъятые" list.
Fix (core/seizure.py `list_seized`): now filters to
  seizure_reason in {credit_default, durability_zero}
  AND is_zero_business != True (plus a level-0 embedded-doc guard)
  AND not returned (returned_to_owner!=True, status!=cancelled).
Result: leased level-0 and inactivity seizures no longer appear; returned-to-work ones disappear.
(Seizure engine already excluded level-0 from being seized; the bug was in the display query + stale data.)

### Task 2 — Level-0 businesses bought BEFORE the lease update had no 3-day timer
Fix (server.py startup_event, idempotent one-time backfill):
  For businesses level=0, is_zero_business=True, missing expires_at →
  set expires_at = now + 3 days (zero_lease.compute_expires_at) + zero_lease_backfilled_at.
  Also mirrors expires_at into the plot's embedded business doc.
  Idempotent: never overwrites an existing expires_at, so deploys do NOT renew the lease.
Also: strips stale is_seized flags off level-0 marketplace listings and re-runs
restore_wrongly_seized_zero_leases so wrongly-seized leased businesses resume.

### Lease expiry behaviour (already correct, verified)
On expiry (zero_lease._expire_zero_business): business deleted, plot deleted (cell becomes
"Available"), auto marketplace listing deleted, pulled from user.businesses_owned, T3 bonus clawed back.
→ Business does NOT stay on the marketplace after expiry; cell is free as if never rented.

### Verification (screenshots taken from running app, ru locale)
- My Businesses timer: fresh "2д 22:57" (cyan), ~2h "01:59" (yellow/urgent <12h), expired "Истекла" (red).
- Map cell (28,16) detail: owned Lv.0 (Owner: LeaseTester) → after sweep Owner: Available + Buy (Lv.0, 0 $CITY).
- process_zero_lease() confirmed: business/plot/listing all removed after expiry.
- list_seized unit test: only credit_default + durability_zero (non-zero, not returned) shown.

## Files touched
- core/seizure.py — list_seized query + level-0 guard
- server.py — startup backfill of expires_at + stale-seizure cleanup for level-0 listings
- backend/seed_zero_lease_demo.py — NEW dev-only seed helper for lease UI states

## Backlog / next
- P1: surface remaining lease time in the map cell detail popup (currently only in "Мои бизнесы").
- P2: admin view for inactivity-seized businesses (now intentionally excluded from "Изъятые").
