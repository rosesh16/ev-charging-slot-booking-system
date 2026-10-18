# EV Charging Slot Booking System

[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django%20REST%20Framework-3.18-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Nginx](https://img.shields.io/badge/Nginx-Alpine-009639.svg)](https://nginx.org/)
[![Docker](https://img.shields.io/badge/Docker%20Compose-v2-2496ED.svg)](https://www.docker.com/)

A production-ready, containerized REST API backend for managing electric vehicle (EV) charging stations, charger discovery, driver vehicle registration, and charging slot reservations with guaranteed database-level booking overlap prevention.

---

## 1. Project Purpose & Overview

The **EV Charging Slot Booking System** addresses public charging queue friction and reservation contention by providing:
- **Station & Charger Discovery**: Public discovery of operational stations and individual chargers, filtering out inactive or offline equipment.
- **Vehicle Profiles**: Owner-scoped electric vehicle registration with battery capacity specifications.
- **Guaranteed Slot Conflict Prevention**: Mathematical exclusion constraint enforcement on time intervals (`TSTZRANGE` with `btree_gist`), guaranteeing zero double-bookings even under concurrent race conditions.
- **Lifecycle Management**: 30-minute reservation windows, unstarted booking cancellations, and instantaneous slot re-availability.
- **Edge Security & Routing**: Internal container network shielding with Nginx reverse proxy handling client requests and forwarding standard proxy headers.

---

## 2. Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Language** | Python 3.10 | Standard runtime across host and containers |
| **Framework** | Django 5.2 | Web framework, ORM, custom User model |
| **API Engine** | Django REST Framework 3.18 | Token authentication, serializer validation |
| **Database** | PostgreSQL 17 | `btree_gist` extension, `TSTZRANGE` exclusion constraints |
| **App Server** | Gunicorn 23.0 | WSGI server with 3 sync workers on internal port 8000 |
| **Reverse Proxy** | Nginx (Alpine) | Reverse proxy on internal port 80, published to localhost |
| **Containerization** | Docker Compose | Multi-service orchestration (`db`, `web`, `nginx`) |

---

## 3. Architecture & Container Topology

The application runs as three decoupled services within an internal Docker bridge network:

```
[ Client / Browser / curl ]
            │
            ▼ (HTTP on 127.0.0.1:8080 or :8081)
┌────────────────────────────────────────────────────────┐
│ Nginx Reverse Proxy (service: nginx)                  │
│ Port 80 internal                                       │
└───────────────────────────┬────────────────────────────┘
                            │ (HTTP internal)
                            ▼
┌────────────────────────────────────────────────────────┐
│ Django / Gunicorn WSGI (service: web)                  │
│ Port 8000 internal (unprivileged: appuser)            │
└───────────────────────────┬────────────────────────────┘
                            │ (TCP 5432 internal)
                            ▼
┌────────────────────────────────────────────────────────┐
│ PostgreSQL 17 Database (service: db)                   │
│ Persistent volume: postgres_data                       │
│ Port 5432 internal / 127.0.0.1:5433 host               │
└────────────────────────────────────────────────────────┘
```

Detailed architectural diagrams and flows are available in [docs/diagrams/architecture.md](docs/diagrams/architecture.md).

---

## 4. Prerequisites

Before setting up the project, ensure you have:
- **Git** 2.40+
- **Python** 3.10.x
- **Docker Desktop** (with Linux/WSL2 engine enabled)
- **Docker Compose** v2.20+
- **Windows PowerShell** 5.1+ or Linux/macOS shell

---

## 5. Local Setup Instructions

### 5.1 Clone the Repository
```powershell
git clone https://github.com/rosesh16/ev-charging-slot-booking-system.git C:\DevOps_Project
cd C:\DevOps_Project
```

### 5.2 Environment Configuration (`.env`)
Copy the example template to create your local `.env`:
```powershell
Copy-Item .env.example .env
```

Generate a secure Django `SECRET_KEY` and insert it into `.env`:
```powershell
python -c "import secrets; from pathlib import Path; p = Path('.env'); content = p.read_text(); p.write_text(content.replace('your_django_secret_key_here', secrets.token_urlsafe(50)))"
```

> [!NOTE]
> **Port Configuration**: By default, Nginx binds to `127.0.0.1:8080`. If port 8080 is already occupied by another local service on your machine (such as Jenkins or Java), set `NGINX_PORT=8081` in your `.env` file before launching.

### 5.3 Build and Start the Containers
```powershell
docker compose up -d --build
```

Verify that all services are operational:
```powershell
docker compose ps
```

### 5.4 Apply Database Migrations
Apply the initial schema and the PostgreSQL `btree_gist` exclusion constraint migrations:
```powershell
docker compose exec web python manage.py migrate
```

---

## 6. REST API Reference

The root API is exposed through Nginx on `http://127.0.0.1:${NGINX_PORT:-8080}` (e.g. `http://127.0.0.1:8081` if overridden):

| Method | Route | Auth Required | Description |
|---|---|---|---|
| `GET` | `/health/` | Public | System and database connectivity health probe |
| `POST` | `/api/auth/register/` | Public | Register new driver account (returns token) |
| `POST` | `/api/auth/login/` | Public | Authenticate user with email and password |
| `GET` | `/api/vehicles/` | Token | List authenticated user's vehicles |
| `POST` | `/api/vehicles/` | Token | Register a vehicle for authenticated user |
| `GET` | `/api/stations/` | Public | List all active charging stations |
| `GET` | `/api/stations/<id>/` | Public | Retrieve active station detail with chargers |
| `GET` | `/api/chargers/` | Public | List active chargers (supports `?station=<id>`) |
| `GET` | `/api/bookings/` | Token | List authenticated user's bookings |
| `POST` | `/api/bookings/` | Token | Reserve a 30-min slot on an active charger |
| `GET` | `/api/bookings/<id>/` | Token | Retrieve authenticated user's booking detail |
| `POST` | `/api/bookings/<id>/cancel/` | Token | Cancel an upcoming unstarted booking |

For full request/response schemas and validation error formats, see [docs/DATA_MODEL_AND_API.md](docs/DATA_MODEL_AND_API.md).

---

## 7. Testing

### 7.1 Running the Automated Test Suite
Run the complete Django test suite (46 tests) inside the containerized environment:
```powershell
docker compose exec web python manage.py test
```

### 7.2 Running Concurrency Exclusion Tests
Execute the PostgreSQL concurrent race condition test in isolation:
```powershell
docker compose exec web python manage.py test bookings.tests.PostgresConcurrencyTests -v 2
```

---

## 8. Current Limitations & Deferred Features

The backend REST API is fully functional for core driver reservation workflows. The following features are currently out of scope and planned for future iterations:
- **Graphical Web Frontend**: The project currently provides a headless REST API. Frontend UI journeys remain a planned enhancement.
- **Phone OTP Verification**: The User schema stores phone numbers; SMS provider integration is deferred.
- **OCPP 1.6J / 2.0.1 Integration**: Physical charger hardware telemetry protocol.
- **Payments & Dynamic Tariffs**: Pre-authorization and billing engines.
- **On-Site Arrival Verification**: RFID / QR code scanning.
- **Automated No-Show Cancellation**: Periodic background task queue.
- **CI/CD & Configuration Management**: Jenkins continuous integration pipelines, automated Selenium suites, and Ansible playbooks are scheduled for subsequent DevOps implementation phases.

---

## 9. Documentation Sitemap

- [SRS Specification Summary](docs/SRS_SUMMARY.md)
- [Use Case Diagram (PlantUML)](docs/diagrams/use_case_diagram.puml)
- [Deployment Architecture (Mermaid)](docs/diagrams/architecture.md)
- [Data Model & API Reference](docs/DATA_MODEL_AND_API.md)
- [Local Development Setup](docs/LOCAL_SETUP.md)
- [MVP Acceptance Checklist](docs/MVP_ACCEPTANCE_CHECKLIST.md)
- [Contributing & Branching Guidelines](CONTRIBUTING.md)
