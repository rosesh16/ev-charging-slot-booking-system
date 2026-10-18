# MVP Acceptance Checklist
## EV Charging Slot Booking System

This checklist establishes explicit, testable criteria for validating the Minimum Viable Product (MVP) implementation across functional and infrastructure domains.

> [!NOTE]
> **Status Conventions**:
> - `PASS (CURRENT RUN)`: Explicitly verified with live command execution in the current audit session.
> - `PASS (TEST SUITE)`: Verified by the complete 46-test automated suite executed and passing inside the container during the current session.
> - `NOT RUN (CURRENT RUN)`: Test condition was verified historically in Stage 3, but was not executed live in the current run to avoid intentionally disrupting active database services.
> - `DEFERRED`: Planned future feature acknowledged as out of scope for the current MVP milestone.

---

## 1. Authentication & User Management

| Item ID | Test Criterion | Verification Method | Expected Result | Status |
|---|---|---|---|---|
| **CHK-AUTH-01** | Driver Registration | `POST /api/auth/register/` | Returns `201 Created` with auth `token` and `user` payload; password hashed via PBKDF2; role assigned as `DRIVER`. | `PASS (TEST SUITE)` |
| **CHK-AUTH-02** | Duplicate Email Rejection | `POST /api/auth/register/` with existing email | Returns `400 Bad Request` with validation error on `email`. Case-insensitive uniqueness verified. | `PASS (TEST SUITE)` |
| **CHK-AUTH-03** | Password Validation | `POST /api/auth/register/` with short/common password | Returns `400 Bad Request` rejecting passwords shorter than 8 characters. | `PASS (TEST SUITE)` |
| **CHK-AUTH-04** | Driver Login | `POST /api/auth/login/` with valid credentials | Returns `200 OK` with auth `token` matching stored token in `authtoken_token`. | `PASS (TEST SUITE)` |
| **CHK-AUTH-05** | Invalid Login Handling | `POST /api/auth/login/` with incorrect password | Returns `401 Unauthorized` with `{"detail": "Invalid email or password."}`. | `PASS (TEST SUITE)` |

---

## 2. Vehicle Management & Ownership Isolation

| Item ID | Test Criterion | Verification Method | Expected Result | Status |
|---|---|---|---|---|
| **CHK-VEH-01** | Create Vehicle Profile | `POST /api/vehicles/` with `Authorization: Token <key>` | Returns `201 Created`; server sets `owner=request.user`, ignoring client-supplied user IDs. | `PASS (TEST SUITE)` |
| **CHK-VEH-02** | Registration Uniqueness | `POST /api/vehicles/` with existing plate | Returns `400 Bad Request` preventing duplicate vehicle registration numbers. | `PASS (TEST SUITE)` |
| **CHK-VEH-03** | User Vehicle Isolation | `GET /api/vehicles/` across two distinct user tokens | Each user retrieves only their own registered vehicles. Zero data leakage across accounts. | `PASS (TEST SUITE)` |
| **CHK-VEH-04** | Unauthenticated Access | `GET /api/vehicles/` without token | Returns `401 Unauthorized`. | `PASS (TEST SUITE)` |

---

## 3. Station and Charger Discovery

| Item ID | Test Criterion | Verification Method | Expected Result | Status |
|---|---|---|---|---|
| **CHK-STN-01** | Active Stations Discovery | `GET /api/stations/` | Returns `200 OK` listing active stations (`is_active=True`). Public access without token. | `PASS (TEST SUITE)` |
| **CHK-STN-02** | Inactive Station Masking | `GET /api/stations/` | Inactive stations (`is_active=False`) are completely excluded from the listing. | `PASS (TEST SUITE)` |
| **CHK-STN-03** | Station Detail with Chargers| `GET /api/stations/<id>/` | Returns `200 OK` with nested active chargers. Inactive station ID returns `404 Not Found`. | `PASS (TEST SUITE)` |
| **CHK-STN-04** | Charger Listing & Filter | `GET /api/chargers/?station=<id>` | Returns `200 OK` with chargers for specified active station. Invalid ID returns `400 Bad Request`. | `PASS (TEST SUITE)` |

---

## 4. Booking Validation & Lifecycle

| Item ID | Test Criterion | Verification Method | Expected Result | Status |
|---|---|---|---|---|
| **CHK-BKG-01** | Valid 30-min Booking | `POST /api/bookings/` with valid vehicle, charger, and 30-min window | Returns `201 Created` with status `CONFIRMED`. | `PASS (TEST SUITE)` |
| **CHK-BKG-02** | Duration Restriction | `POST /api/bookings/` with 15-min or 45-min interval | Returns `400 Bad Request` (`Booking duration must be exactly 30 minutes.`). | `PASS (TEST SUITE)` |
| **CHK-BKG-03** | Future Start Time | `POST /api/bookings/` with start time in the past | Returns `400 Bad Request` (`Booking start time must be in the future.`). | `PASS (TEST SUITE)` |
| **CHK-BKG-04** | Vehicle Ownership Enforcement | `POST /api/bookings/` referencing another user's vehicle | Returns `400 Bad Request` (`The selected vehicle does not belong to you.`). | `PASS (TEST SUITE)` |
| **CHK-BKG-05** | Inactive / Offline Charger | `POST /api/bookings/` on OFFLINE or MAINTENANCE charger | Returns `400 Bad Request` indicating charger is unavailable. | `PASS (TEST SUITE)` |
| **CHK-BKG-06** | Adjacent Slot Acceptance | Two bookings back-to-back: 10:00-10:30 and 10:30-11:00 on same charger | Both succeed with `201 Created` due to half-open interval `[)` handling. | `PASS (TEST SUITE)` |
| **CHK-BKG-07** | Overlap Conflict Rejection | `POST /api/bookings/` overlapping existing active booking | Returns `409 Conflict` (`This charger is already booked for the requested time slot.`). | `PASS (TEST SUITE)` |
| **CHK-BKG-08** | Booking Cancellation | `POST /api/bookings/<id>/cancel/` | Returns `200 OK`, updates status to `CANCELLED` and sets `cancelled_at`. | `PASS (TEST SUITE)` |
| **CHK-BKG-09** | Cancelled Slot Reuse | Booking created on slot previously held by cancelled booking | Returns `201 Created`. Cancelled reservation does not block rebooking. | `PASS (TEST SUITE)` |
| **CHK-BKG-10** | Cross-User Cancellation | User B attempts `POST /api/bookings/<id>/cancel/` on User A's booking | Returns `404 Not Found`. Users cannot cancel or view other users' bookings. | `PASS (TEST SUITE)` |

---

## 5. Concurrency & Database Constraints

| Item ID | Test Criterion | Verification Method | Expected Result | Status |
|---|---|---|---|---|
| **CHK-CONC-01** | High-Concurrency Race | 2 simultaneous threads attempting same charger & time slot via `PostgresConcurrencyTests` | Exactly one thread succeeds (`201 Created`); the other receives `409 Conflict`. Zero double-bookings. | `PASS (TEST SUITE)` |
| **CHK-CONC-02** | Exclusion Constraint | PostgreSQL diagnostic inspection | `no_overlapping_active_charger_bookings` exclusion constraint enforced at database level. | `PASS (TEST SUITE)` |
| **CHK-CONC-03** | Lock Ordering Consistency | Concurrent create & cancel operations | Locks `Charger` row first, then `Booking` row to prevent deadlocks. | `PASS (TEST SUITE)` |

---

## 6. Infrastructure, Docker & Reverse Proxy

| Item ID | Test Criterion | Verification Method | Expected Result | Status |
|---|---|---|---|---|
| **CHK-INFRA-01** | Health Endpoint Probe | `GET /health/` through Nginx (port 8081) | Returns `200 OK` (`{"status":"healthy","database":"connected"}`). | `PASS (CURRENT RUN)` |
| **CHK-INFRA-02** | Database Disconnect Probe | `GET /health/` when database unreachable | Returns `503 Service Unavailable` (`{"status":"unhealthy","database":"disconnected"}`). | `NOT RUN (CURRENT RUN)` |
| **CHK-INFRA-03** | Nginx Reverse Proxy Routing | API requests (`/api/...`) sent to host port (8080/8081) | Nginx proxies to `web:8000`, preserving `Host`, `X-Real-IP`, and `X-Forwarded-*` headers. | `PASS (CURRENT RUN)` |
| **CHK-INFRA-04** | Direct Web Port Shielding | Attempt connecting to `web:8001` or `web:8000` from host | Connection refused / closed. Gunicorn has no published host port. | `PASS (CURRENT RUN)` |
| **CHK-INFRA-05** | Service Startup Ordering | `docker compose up -d` | `web` service starts only after `db` reports `service_healthy`. | `PASS (CURRENT RUN)` |
| **CHK-INFRA-06** | Named Volume Persistence | `docker compose down && docker compose up -d` | Data in `postgres_data` volume is completely preserved across restarts. | `PASS (CURRENT RUN)` |
| **CHK-INFRA-07** | Non-Root Container Execution | Inspect running process inside `web` container | Executes under UID/GID of `appuser:appgroup`. | `PASS (CURRENT RUN)` |
| **CHK-INFRA-08** | Insecure Settings Guard | Inspect Compose configuration | `DEBUG` defaults to `0`; missing `SECRET_KEY` halts startup with error. | `PASS (CURRENT RUN)` |
| **CHK-INFRA-09** | Secret Hygiene | `git check-ignore -v .env` & cached git diff | `.env` ignored; zero secrets committed or tracked. | `PASS (CURRENT RUN)` |

---

## 7. Deferred Features (Future Scope)

| Item ID | Feature | Target Scope | Current Status |
|---|---|---|---|
| **DEF-01** | Phone Number SMS OTP Verification | Driver Verification | `DEFERRED` (Schema stores phone; SMS provider unintegrated) |
| **DEF-02** | OCPP 1.6J / 2.0.1 Protocol Integration | Hardware Communication | `DEFERRED` (Hardware simulation handled by choices) |
| **DEF-03** | Payment Gateway & Pre-Authorization | Billing Engine | `DEFERRED` (Zero fee charging currently) |
| **DEF-04** | RFID / QR Code Physical Check-In | Driver On-Site Arrival | `DEFERRED` (No hardware reader integration) |
| **DEF-05** | No-Show Grace Period Auto-Cancellation | Background Worker | `DEFERRED` (No Celery/Redis background task queue) |
| **DEF-06** | Operator Management Dashboard | Station Operator UI | `DEFERRED` (Operator model role exists; UI deferred) |
| **DEF-07** | Push / Email Notifications | User Communication | `DEFERRED` (No email or push gateway configured) |
