# Data Model and REST API Reference
## EV Charging Slot Booking System

---

## 1. Relational Data Models

The system defines 5 core relational models across 4 Django applications (`accounts`, `vehicles`, `stations`, `bookings`).

### 1.1 `accounts.User`
Custom user model extending `AbstractUser`. Configured via `AUTH_USER_MODEL = "accounts.User"`.

| Field Name | Type | Constraints / Attributes | Description |
|---|---|---|---|
| `id` | BigAutoField | Primary Key | Unique user identifier |
| `email` | EmailField | `unique=True`, `max_length=254` | Primary login credential (`USERNAME_FIELD`) |
| `username` | CharField | `max_length=150`, `REQUIRED_FIELDS` | Human-readable user handle |
| `password` | CharField | `max_length=128`, PBKDF2-SHA256 | Hashed account password |
| `phone_number`| CharField | `max_length=20`, `blank=True` | Contact phone number |
| `role` | CharField | `max_length=10`, Choices: `DRIVER`, `OPERATOR`, default: `DRIVER` | User authorization role |
| `is_active` | BooleanField | default: `True` | Account active flag |
| `date_joined` | DateTimeField | auto-generated | Registration timestamp |

---

### 1.2 `vehicles.Vehicle`
Represents an electric vehicle owned by a registered driver.

| Field Name | Type | Constraints / Attributes | Description |
|---|---|---|---|
| `id` | BigAutoField | Primary Key | Unique vehicle identifier |
| `owner` | ForeignKey | `accounts.User`, `on_delete=CASCADE`, `related_name="vehicles"` | Vehicle owner reference |
| `registration_number` | CharField | `max_length=20`, `unique=True` | Official vehicle license plate / reg number |
| `make` | CharField | `max_length=100` | Manufacturer name (e.g. Tesla, Hyundai) |
| `model` | CharField | `max_length=100` | Vehicle model name (e.g. Model 3, Ioniq 5) |
| `battery_capacity_kwh`| DecimalField| `max_digits=6`, `decimal_places=2`, `null=True`, `blank=True` | Battery pack size in kilowatt-hours |
| `created_at` | DateTimeField| `auto_now_add=True` | Vehicle record creation timestamp |

---

### 1.3 `stations.Station`
Physical charging station location hosting one or more chargers.

| Field Name | Type | Constraints / Attributes | Description |
|---|---|---|---|
| `id` | BigAutoField | Primary Key | Unique station identifier |
| `name` | CharField | `max_length=150` | Station name |
| `address` | CharField | `max_length=255` | Street address |
| `city` | CharField | `max_length=100` | City name |
| `latitude` | DecimalField| `max_digits=9`, `decimal_places=6`, `null=True`, `blank=True` | GPS latitude coordinates |
| `longitude` | DecimalField| `max_digits=9`, `decimal_places=6`, `null=True`, `blank=True` | GPS longitude coordinates |
| `is_active` | BooleanField| default: `True` | Active status (inactive stations hidden from discovery) |
| `created_at` | DateTimeField| `auto_now_add=True` | Creation timestamp |

---

### 1.4 `stations.Charger`
Individual charging point attached to a station.

| Field Name | Type | Constraints / Attributes | Description |
|---|---|---|---|
| `id` | BigAutoField | Primary Key | Unique charger identifier |
| `station` | ForeignKey | `stations.Station`, `on_delete=PROTECT`, `related_name="chargers"` | Parent station reference |
| `name` | CharField | `max_length=100` | Point/stall name (e.g. "Stall 1A") |
| `connector_type`| CharField | `max_length=20`, Choices: `TYPE_2`, `CCS2`, `CHADEMO` | Physical charging plug type |
| `power_kw` | DecimalField| `max_digits=6`, `decimal_places=2` | Maximum output power rating in kW |
| `status` | CharField | `max_length=15`, Choices: `AVAILABLE`, `OCCUPIED`, `OFFLINE`, `MAINTENANCE` | Operational simulation status |
| `is_active` | BooleanField| default: `True` | Active status |

#### Constraints:
- `UniqueConstraint(fields=["station", "name"], name="unique_charger_name_per_station")`

---

### 1.5 `bookings.Booking`
Time-slot reservation for a charger.

| Field Name | Type | Constraints / Attributes | Description |
|---|---|---|---|
| `id` | BigAutoField | Primary Key | Unique booking identifier |
| `user` | ForeignKey | `accounts.User`, `on_delete=PROTECT`, `related_name="bookings"` | Reserving driver reference |
| `vehicle` | ForeignKey | `vehicles.Vehicle`, `on_delete=PROTECT`, `related_name="bookings"` | Vehicle to be charged |
| `charger` | ForeignKey | `stations.Charger`, `on_delete=PROTECT`, `related_name="bookings"` | Reserved charger reference |
| `start_time` | DateTimeField| `start_time` (UTC timestamp) | Slot start time |
| `end_time` | DateTimeField| `end_time` (UTC timestamp) | Slot end time |
| `status` | CharField | `max_length=12`, Choices: `PENDING`, `CONFIRMED`, `CANCELLED`, `COMPLETED` | Booking lifecycle status |
| `created_at` | DateTimeField| `auto_now_add=True` | Booking submission timestamp |
| `cancelled_at` | DateTimeField| `null=True`, `blank=True` | Timestamp when booking was cancelled |

#### Constraints & Migrations:
1. **CheckConstraint**: `condition=Q(end_time__gt=F("start_time"))`, `name="booking_end_after_start"`
2. **PostgreSQL Extension Migration**: `BtreeGistExtension()` (migration `0002_enable_btree_gist`)
3. **ExclusionConstraint** (migration `0003_booking_no_overlapping_active_charger_bookings`):
   ```python
   ExclusionConstraint(
       name="no_overlapping_active_charger_bookings",
       expressions=[
           ("charger", RangeOperators.EQUAL),
           (
               Func(
                   F("start_time"),
                   F("end_time"),
                   Value("[)"),
                   function="TSTZRANGE",
                   output_field=DateTimeRangeField(),
               ),
               RangeOperators.OVERLAPS,
           ),
       ],
       condition=~Q(status="CANCELLED"),
   )
   ```

---

## 2. Complete REST API Reference

All routes are mounted under the root URL configuration in [config/urls.py](file:///c:/DevOps_Project/config/urls.py).

### 2.1 API Endpoint Summary Table

| Method | Exact Route | Auth Required | Purpose | Request Body / Parameters | Success Codes | Error Codes |
|---|---|---|---|---|---|---|
| `GET` | `/health/` | Public | System and database health check probe | None | `200 OK` | `503 Service Unavailable` |
| `POST` | `/api/auth/register/` | Public | Register new driver account | `email`, `username`, `password`, `phone_number` (opt) | `201 Created` | `400 Bad Request` |
| `POST` | `/api/auth/login/` | Public | Obtain authentication token | `email`, `password` | `200 OK` | `400 Bad Request`, `401 Unauthorized` |
| `GET` | `/api/vehicles/` | Token | List authenticated user's vehicles | None | `200 OK` | `401 Unauthorized` |
| `POST` | `/api/vehicles/` | Token | Register a vehicle for authenticated user | `make`, `model`, `registration_number`, `battery_capacity_kwh` (opt) | `201 Created` | `400 Bad Request`, `401 Unauthorized` |
| `GET` | `/api/stations/` | Public | List all active charging stations | None | `200 OK` | None |
| `GET` | `/api/stations/<id>/` | Public | Retrieve active station and its active chargers | URL parameter `id` (integer) | `200 OK` | `404 Not Found` |
| `GET` | `/api/chargers/` | Public | List active chargers (with optional station filter) | Query parameter `?station=<id>` (opt) | `200 OK` | `400 Bad Request` |
| `GET` | `/api/bookings/` | Token | List authenticated user's bookings | None | `200 OK` | `401 Unauthorized` |
| `POST` | `/api/bookings/` | Token | Book a 30-minute charging slot | `charger`, `vehicle`, `start_time`, `end_time` | `201 Created` | `400 Bad Request`, `401 Unauthorized`, `409 Conflict`, `500 Internal Error` |
| `GET` | `/api/bookings/<id>/` | Token | Retrieve authenticated user's booking detail | URL parameter `id` (integer) | `200 OK` | `401 Unauthorized`, `404 Not Found` |
| `POST` | `/api/bookings/<id>/cancel/` | Token | Cancel upcoming, unstarted booking | URL parameter `id` (integer) | `200 OK` | `400 Bad Request`, `401 Unauthorized`, `404 Not Found` |

---

## 3. Endpoint Details, Payloads, and Responses

### 3.1 Health Check Probe
- **Route**: `GET /health/`
- **Authentication**: None (`AllowAny`)
- **Success Response (`200 OK`)**:
  ```json
  {
    "status": "healthy",
    "database": "connected"
  }
  ```
- **Failure Response (`503 Service Unavailable`)**:
  ```json
  {
    "status": "unhealthy",
    "database": "disconnected"
  }
  ```

---

### 3.2 User Registration
- **Route**: `POST /api/auth/register/`
- **Authentication**: None (`AllowAny`)
- **Request Body**:
  ```json
  {
    "email": "driver@example.com",
    "username": "driver1",
    "password": "StrongPassword123!",
    "phone_number": "+1234567890"
  }
  ```
- **Success Response (`201 Created`)**:
  ```json
  {
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "user": {
      "id": 1,
      "email": "driver@example.com",
      "username": "driver1",
      "phone_number": "+1234567890",
      "role": "DRIVER"
    }
  }
  ```
- **Error Responses (`400 Bad Request`)**:
  - Duplicate email: `{"email": ["A user with this email already exists."]}`
  - Weak password: `{"password": ["This password is too short. It must contain at least 8 characters."]}`

---

### 3.3 User Login
- **Route**: `POST /api/auth/login/`
- **Authentication**: None (`AllowAny`)
- **Request Body**:
  ```json
  {
    "email": "driver@example.com",
    "password": "StrongPassword123!"
  }
  ```
- **Success Response (`200 OK`)**:
  ```json
  {
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "user": {
      "id": 1,
      "email": "driver@example.com",
      "username": "driver1",
      "phone_number": "+1234567890",
      "role": "DRIVER"
    }
  }
  ```
- **Error Response (`401 Unauthorized`)**:
  `{"detail": "Invalid email or password."}`

---

### 3.4 Vehicle List & Create
- **Route**: `GET /api/vehicles/` and `POST /api/vehicles/`
- **Authentication**: Token (`Authorization: Token <token>`)
- **POST Request Body**:
  ```json
  {
    "make": "Tesla",
    "model": "Model 3",
    "registration_number": "EV-1234",
    "battery_capacity_kwh": 75.00
  }
  ```
- **Success Response (`201 Created`)**:
  ```json
  {
    "id": 1,
    "owner": 1,
    "registration_number": "EV-1234",
    "make": "Tesla",
    "model": "Model 3",
    "battery_capacity_kwh": "75.00",
    "created_at": "2026-10-18T10:00:00Z"
  }
  ```
- **GET Response (`200 OK`)**: List of vehicles owned exclusively by the authenticated user.

---

### 3.5 Stations Discovery
- **Route**: `GET /api/stations/`
- **Authentication**: None (`AllowAny`)
- **Success Response (`200 OK`)**:
  ```json
  [
    {
      "id": 1,
      "name": "Downtown Charging Hub",
      "address": "123 Main St",
      "city": "Metropolis",
      "latitude": "37.774929",
      "longitude": "-122.419416",
      "is_active": true,
      "created_at": "2026-10-18T08:00:00Z"
    }
  ]
  ```

---

### 3.6 Station Detail
- **Route**: `GET /api/stations/<id>/`
- **Authentication**: None (`AllowAny`)
- **Success Response (`200 OK`)**:
  ```json
  {
    "id": 1,
    "name": "Downtown Charging Hub",
    "address": "123 Main St",
    "city": "Metropolis",
    "latitude": "37.774929",
    "longitude": "-122.419416",
    "is_active": true,
    "chargers": [
      {
        "id": 10,
        "name": "Stall 1A",
        "connector_type": "CCS2",
        "power_kw": "150.00",
        "status": "AVAILABLE",
        "is_active": true
      }
    ],
    "created_at": "2026-10-18T08:00:00Z"
  }
  ```
- **Error Response (`404 Not Found`)**: When station does not exist or has `is_active=False`.

---

### 3.7 Chargers Discovery
- **Route**: `GET /api/chargers/` or `GET /api/chargers/?station=1`
- **Authentication**: None (`AllowAny`)
- **Success Response (`200 OK`)**:
  ```json
  [
    {
      "id": 10,
      "station": {
        "id": 1,
        "name": "Downtown Charging Hub",
        "address": "123 Main St",
        "city": "Metropolis"
      },
      "name": "Stall 1A",
      "connector_type": "CCS2",
      "power_kw": "150.00",
      "status": "AVAILABLE",
      "is_active": true
    }
  ]
  ```
- **Error Response (`400 Bad Request`)**: When `?station=999` is an inactive or non-existent station ID.

---

### 3.8 Booking Creation
- **Route**: `POST /api/bookings/`
- **Authentication**: Token (`Authorization: Token <token>`)
- **Request Body**:
  ```json
  {
    "charger": 10,
    "vehicle": 1,
    "start_time": "2026-10-20T10:00:00Z",
    "end_time": "2026-10-20T10:30:00Z"
  }
  ```
- **Success Response (`201 Created`)**:
  ```json
  {
    "id": 101,
    "user": 1,
    "vehicle": {
      "id": 1,
      "owner": 1,
      "registration_number": "EV-1234",
      "make": "Tesla",
      "model": "Model 3",
      "battery_capacity_kwh": "75.00",
      "created_at": "2026-10-18T10:00:00Z"
    },
    "charger": {
      "id": 10,
      "station": {
        "id": 1,
        "name": "Downtown Charging Hub",
        "address": "123 Main St",
        "city": "Metropolis"
      },
      "name": "Stall 1A",
      "connector_type": "CCS2",
      "power_kw": "150.00",
      "status": "AVAILABLE",
      "is_active": true
    },
    "start_time": "2026-10-20T10:00:00Z",
    "end_time": "2026-10-20T10:30:00Z",
    "status": "CONFIRMED",
    "created_at": "2026-10-18T10:15:00Z",
    "cancelled_at": null
  }
  ```
- **Validation Errors (`400 Bad Request`)**:
  - Non-30 minute duration: `{"end_time": ["Booking duration must be exactly 30 minutes."]}`
  - Past start time: `{"start_time": ["Booking start time must be in the future."]}`
  - Unowned vehicle: `{"vehicle": ["The selected vehicle does not belong to you."]}`
  - Inactive/offline charger: `{"charger": ["Selected charger is inactive."]}`
- **Conflict Error (`409 Conflict`)**:
  - Slot overlap detected: `{"detail": "This charger is already booked for the requested time slot."}`

---

### 3.9 Booking Cancellation
- **Route**: `POST /api/bookings/<id>/cancel/`
- **Authentication**: Token (`Authorization: Token <token>`)
- **Success Response (`200 OK`)**:
  ```json
  {
    "id": 101,
    "user": 1,
    "vehicle": { ... },
    "charger": { ... },
    "start_time": "2026-10-20T10:00:00Z",
    "end_time": "2026-10-20T10:30:00Z",
    "status": "CANCELLED",
    "created_at": "2026-10-18T10:15:00Z",
    "cancelled_at": "2026-10-18T10:20:00Z"
  }
  ```
- **Error Responses**:
  - Not found or not owned: `404 Not Found` (`{"detail": "Booking not found."}`)
  - Already cancelled: `400 Bad Request` (`{"detail": "This booking is already cancelled."}`)
  - Booking in past/started: `400 Bad Request` (`{"detail": "Cannot cancel a booking that has already started or ended."}`)
