# Software Requirements Specification (SRS) Summary
## Electric Vehicle (EV) Charging Slot Booking System

---

## 1. Project Purpose and Problem Statement

### 1.1 Purpose
The EV Charging Slot Booking System is a backend RESTful service designed to allow electric vehicle drivers to locate active charging stations, discover available chargers, and book guaranteed 30-minute charging time slots in advance. The system eliminates uncertainty at charging stations by enforcing strict concurrency and slot conflict prevention at the database level.

### 1.2 Problem Statement
Public EV charging infrastructure frequently suffers from:
- **Queueing and Wait Times**: Drivers arrive at charging stations without knowing if a charger is occupied or reserved.
- **Double-Booking & Race Conditions**: High-contention time slots are prone to simultaneous booking attempts, which naive application-layer locks fail to prevent under horizontal scaling.
- **Incompatible Chargers & Unauthorized Access**: Drivers need clarity on connector types (Type 2, CCS2, CHAdeMO) and require secure, authenticated ownership of booked resources.

---

## 2. System Objectives and Stakeholders

### 2.1 Objectives
- Provide a robust REST API for user authentication, vehicle management, station discovery, and slot reservations.
- Guarantee zero double-booking on any individual charger using database-enforced exclusion constraints.
- Provide containerized, production-grade deployment architecture with reverse-proxy routing and service health checks.
- Maintain a comprehensive automated test suite (currently 46 tests) validating API contracts and high-concurrency race conditions.

### 2.2 Stakeholders
- **EV Drivers**: Primary end users who register, manage vehicles, discover stations/chargers, create bookings, and cancel reservations.
- **Charging Station Operators**: Stakeholders responsible for physical infrastructure (hardware, maintenance status). *(Role model defined; operator-specific management dashboard and APIs are deferred).*
- **DevOps / System Administrators**: Operators who deploy, configure, and monitor containerized services (Nginx, Gunicorn/Django, PostgreSQL).

---

## 3. System Boundary and Deployment Assumptions

### 3.1 System Boundary
- **In Scope (Current MVP)**:
  - Token-based driver authentication (registration, login).
  - Driver vehicle profile management.
  - Public read-only station and charger discovery (filtering active stations and chargers).
  - 30-minute slot reservation with database-level conflict exclusion (`TSTZRANGE` and PostgreSQL `btree_gist`).
  - Booking cancellation and immediate slot reuse.
  - Multi-container Docker Compose setup (Nginx reverse proxy, Django/Gunicorn app, PostgreSQL 17 database).
  - Local HTTP deployment isolated to `127.0.0.1`.
- **Out of Scope / Deferred**:
  - Payment gateway integration, billing, dynamic pricing, and refunds.
  - OCPP (Open Charge Point Protocol 1.6J/2.0.1) hardware telemetry.
  - RFID card or QR code on-site check-in.
  - Real-time WebSockets / SMS / Email notifications.
  - Operator station management portals and admin management dashboards.

### 3.2 Deployment Assumptions
- Service runs via Docker Compose on Linux or Windows WSL2.
- PostgreSQL 17 runs on the internal Compose network (`db:5432`) with persistent storage (`postgres_data`).
- Django/Gunicorn runs as an unprivileged service (`web:8000`), completely shielded from direct public host exposure.
- Nginx acts as the single reverse proxy gateway published on `127.0.0.1:${NGINX_PORT:-8080}`.
- Local HTTP deployment without TLS/HTTPS certificates.

---

## 4. User Roles and Use Cases

### 4.1 Defined Roles
- **DRIVER** (`accounts.User.Role.DRIVER`): Default registered user. Allowed to manage own vehicles, view active stations/chargers, create 30-minute bookings, view own bookings, and cancel own bookings.
- **OPERATOR** (`accounts.User.Role.OPERATOR`): Defined in model schema choices for charging point operators. *(Role-based operator endpoints are deferred; registration defaults strictly to DRIVER to prevent role escalation).*

### 4.2 Use Cases Summary
- **UC-01: Register Driver Account**: Public registration with email, username, and password; returns auth token.
- **UC-02: Authenticate Driver**: Login with email and password; returns auth token.
- **UC-03: Manage Vehicles**: Authenticated driver registers vehicle make, model, registration number, and battery capacity.
- **UC-04: Discover Active Stations**: Publicly list all active stations.
- **UC-05: View Station Details & Chargers**: Retrieve active station info with nested active chargers.
- **UC-06: Filter Chargers**: List active chargers, optionally filtered by station ID query parameter.
- **UC-07: Reserve Charging Slot**: Book an active charger for exactly 30 minutes in the future for an owned vehicle.
- **UC-08: View Bookings**: List all past and upcoming bookings for the authenticated user.
- **UC-09: Cancel Booking**: Cancel an upcoming, unstarted booking; immediately frees slot for rebooking.
- **UC-10: Check System Health**: Public probe verifying web application and PostgreSQL database connectivity.

---

## 5. Functional Requirements

### 5.1 Authentication & Accounts
- **FR-01**: The system shall provide a `POST /api/auth/register/` endpoint allowing new drivers to register with email, username, and password.
- **FR-02**: Email addresses shall be unique (case-insensitive) across all user accounts.
- **FR-03**: Password validation shall enforce Django's standard password complexity rules.
- **FR-04**: Successful registration shall automatically assign the `DRIVER` role and return a REST Framework authentication token.
- **FR-05**: The system shall provide a `POST /api/auth/login/` endpoint authenticating users by email and password, returning an auth token.

### 5.2 Vehicle Management
- **FR-06**: Authenticated drivers shall register vehicles via `POST /api/vehicles/` with `make`, `model`, and unique `registration_number`.
- **FR-07**: The vehicle owner shall be strictly set to the authenticated user from the request context, ignoring any user ID in the request body.
- **FR-08**: Vehicle registration numbers shall be unique across the platform.
- **FR-09**: Authenticated drivers shall list only their own vehicles via `GET /api/vehicles/`.

### 5.3 Stations & Chargers Discovery
- **FR-10**: The system shall provide `GET /api/stations/` listing only active stations (`is_active=True`) without authentication.
- **FR-11**: The system shall provide `GET /api/stations/<id>/` returning station details and its active chargers. Inactive stations shall return HTTP 404.
- **FR-12**: The system shall provide `GET /api/chargers/` listing active chargers with station summary.
- **FR-13**: `GET /api/chargers/?station=<id>` shall filter chargers by station ID, returning HTTP 400 if the station ID is invalid or inactive.

### 5.4 Booking Management & Concurrency
- **FR-14**: Authenticated drivers shall create bookings via `POST /api/bookings/` specifying `charger`, `vehicle`, `start_time`, and `end_time`.
- **FR-15**: Booking duration must be exactly 30 minutes (`end_time - start_time == timedelta(minutes=30)`).
- **FR-16**: Booking `start_time` must be in the future (`start_time > timezone.now()`).
- **FR-17**: The selected vehicle must belong to the authenticated driver.
- **FR-18**: The selected charger and its parent station must be active (`is_active=True`), and charger status must not be `OFFLINE` or `MAINTENANCE`.
- **FR-19**: The system shall prevent overlapping bookings for the same charger across active (non-cancelled) bookings.
- **FR-20**: Adjacent time slots (e.g. 10:00-10:30 and 10:30-11:00) shall be accepted without conflict (`[)` half-open interval).
- **FR-21**: Simultaneous booking requests shall serialize through database row locking (`select_for_update`) and PostgreSQL exclusion constraint (`no_overlapping_active_charger_bookings`). Overlapping booking attempts shall return HTTP 409 Conflict.
- **FR-22**: Authenticated drivers shall list only their own bookings via `GET /api/bookings/` and retrieve booking details via `GET /api/bookings/<id>/`. Non-owned bookings shall return HTTP 404.
- **FR-23**: Authenticated drivers shall cancel unstarted bookings via `POST /api/bookings/<id>/cancel/`. Cancellation shall update status to `CANCELLED` and set `cancelled_at`.
- **FR-24**: Cancelled bookings shall no longer block subsequent reservations for that charger and time range.

### 5.5 System Monitoring
- **FR-25**: The system shall provide a `GET /health/` endpoint verifying active database connectivity without authentication, returning HTTP 200 when healthy and HTTP 503 when the database is unreachable.

---

## 6. Non-Functional Requirements

### 6.1 Reliability & Data Integrity
- **NFR-01**: Booking exclusion constraints must be enforced by PostgreSQL (`btree_gist` extension with `TSTZRANGE` overlap operator `&&`). Application-level checks serve only as pre-checks; database constraint is the final authority.
- **NFR-02**: All booking creation and cancellation operations shall execute within atomic database transactions (`transaction.atomic()`).
- **NFR-03**: Lock acquisition order must be consistent (`Charger` locked first, then `Booking`) to prevent database deadlocks during concurrent creation and cancellation.

### 6.2 Security
- **NFR-04**: Passwords must be securely hashed using PBKDF2 with SHA-256 before storage.
- **NFR-05**: Endpoints modifying or retrieving user data must require HTTP Token Authentication (`Authorization: Token <key>`).
- **NFR-06**: The application container (`web`) shall run as an unprivileged, non-root user (`appuser:appgroup`).
- **NFR-07**: Sensitive credentials (`POSTGRES_PASSWORD`, `SECRET_KEY`) must never be hardcoded into images or committed to version control; they must be supplied via environment variables.
- **NFR-08**: The application shall disable debug mode by default (`DEBUG=0`) in containerized deployments.

### 6.3 Performance & Scalability
- **NFR-09**: Web tier runs Gunicorn WSGI with 3 worker processes.
- **NFR-10**: Nginx reverse proxy buffers client requests, compresses responses, and forwards standard client headers (`Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`).
- **NFR-11**: Containerized services must start in health-dependent order: `web` starts only after `db` passes its `pg_isready` health check.

---

## 7. Constraints, Assumptions, and Traceability

### 7.1 Scope Classification Matrix

| Feature / Requirement | Status | Implemented Components | Traceability / Tests |
|---|---|---|---|
| User Registration & Login | **Implemented & Verified** | `accounts` app, `User` model, DRF token auth | `AuthenticationApiTests` (7 tests) |
| Vehicle Profile Management | **Implemented & Verified** | `vehicles` app, `Vehicle` model, DRF views | `VehicleApiTests` (6 tests) |
| Station Discovery & Filtering | **Implemented & Verified** | `stations` app, `Station` & `Charger` models | `StationAndChargerApiTests` (7 tests) |
| Exact 30-min Booking Validation | **Implemented & Verified** | `bookings` app, `BookingCreateSerializer` | `BookingApiTests` |
| Zero Double-Booking Exclusion | **Implemented & Verified** | PostgreSQL `btree_gist`, `ExclusionConstraint` | `BookingOverlapConstraintTests` (4 tests) |
| High-Concurrency Race Handling | **Implemented & Verified** | `select_for_update()`, atomic transactions | `PostgresConcurrencyTests` (1 test) |
| Booking Cancellation & Reuse | **Implemented & Verified** | `BookingCancelView`, consistent lock ordering | `BookingApiTests` |
| Health Check Probe | **Implemented & Verified** | `config.views.HealthCheckView` (`/health/`) | Manual curl / Python HTTP tests |
| Dockerized Multi-Container Setup | **Implemented & Verified** | `Dockerfile`, `compose.yaml`, `web` & `db` | Docker test run (46 tests pass) |
| Nginx Reverse Proxy Gateway | **Implemented & Verified** | `nginx/default.conf`, `compose.yaml` | HTTP verification on `127.0.0.1:8081` |
| Phone Number OTP Verification | **Deferred** | None (field stored only) | Out of scope for current MVP |
| OCPP 1.6J / 2.0.1 Protocol | **Deferred** | None | Out of scope for current MVP |
| Payment Gateway & Refund Engine | **Deferred** | None | Out of scope for current MVP |
| Driver On-site Check-in / QR | **Deferred** | None | Out of scope for current MVP |
| No-show Auto-cancellation Daemon | **Deferred** | None | Out of scope for current MVP |
| Operator Management Dashboard | **Deferred** | None | Out of scope for current MVP |
| Push / SMS / Email Notifications | **Deferred** | None | Out of scope for current MVP |
