# Local Development and Setup Guide
## EV Charging Slot Booking System

This guide provides step-by-step, reproducible instructions for running the EV Charging Slot Booking System on Windows using PowerShell, Docker Desktop, and Python 3.10+.

---

## 1. Prerequisites and Versions

Ensure the following tools are installed and operational on your system:

| Tool | Recommended Version | Verification Command |
|---|---|---|
| **Git** | 2.40+ | `git --version` |
| **Python** | 3.10.x | `python --version` |
| **Docker Desktop** | 4.25+ (WSL2 backend) | `docker --version` |
| **Docker Compose** | v2.20+ | `docker compose version` |
| **Windows PowerShell**| 5.1 or PowerShell 7+ | `$PSVersionTable.PSVersion` |

---

## 2. Clone and Initial Setup

Clone the repository and enter the project root directory:

```powershell
git clone https://github.com/rosesh16/ev-charging-slot-booking-system.git C:\DevOps_Project
Set-Location C:\DevOps_Project
```

---

## 3. Environment Configuration (`.env`)

The project uses `.env` to supply database credentials and Django settings. A template is provided in [.env.example](file:///c:/DevOps_Project/.env.example).

### 3.1 Copy the Example File
```powershell
Copy-Item .env.example .env
```

### 3.2 Generate and Insert a Secure Secret Key
Generate a cryptographically secure random string and append it directly to `.env` without echoing the key into the console or terminal history:

```powershell
python -c "import secrets; from pathlib import Path; p = Path('.env'); content = p.read_text(); p.write_text(content.replace('your_django_secret_key_here', secrets.token_urlsafe(50)))"
```

### 3.3 Check for Local Port Conflicts
Inspect whether default ports `8080` (Nginx) or `5433` (Postgres host forward) are occupied by other local services:

```powershell
# Check if port 8080 is in use
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue

# If port 8080 is occupied, set NGINX_PORT to 8081 in .env:
(Get-Content .env) -replace 'NGINX_PORT=8080', 'NGINX_PORT=8081' | Set-Content .env
```

> [!NOTE]
> `.env` is strictly ignored by Git (`.gitignore:16:.env`). **Never** commit `.env` or paste actual passwords into public repositories.

---

## 4. Starting the Services

Run Docker Compose to build the Django application image and start all containers:

```powershell
docker compose up -d --build
```

Docker Compose initiates the services in order:
1. Starts `db` (`postgres:17`).
2. Awaits the `pg_isready` health check on `db`.
3. Starts `web` (`python:3.10-slim` running Gunicorn).
4. Starts `nginx` (`nginx:alpine` reverse proxy).

### 4.1 Verify Service Status
```powershell
docker compose ps
```
Expected output:
```
NAME                     IMAGE                COMMAND                  SERVICE   STATUS                 PORTS
devops_project-db-1      postgres:17          "docker-entrypoint.s…"   db        Up (healthy)           127.0.0.1:5433->5432/tcp
devops_project-nginx-1   nginx:alpine         "/docker-entrypoint.…"   nginx     Up                     127.0.0.1:8081->80/tcp
devops_project-web-1     devops_project-web   "gunicorn --bind 0.0…"   web       Up                     8000/tcp
```

### 4.2 Inspect Container Logs
```powershell
# Check Gunicorn and Nginx output
docker compose logs --tail=25 web nginx
```

---

## 5. Applying Database Migrations Safely

Apply all database migrations explicitly inside the running Django container:

```powershell
docker compose exec web python manage.py migrate
```

Verify that all migrations have executed:
```powershell
docker compose exec web python manage.py showmigrations
```
Expected: All migrations under `accounts`, `auth`, `authtoken`, `stations`, `vehicles`, and `bookings` show `[X]`.

> [!CAUTION]
> Do not modify or roll back existing migrations unless instructed. `0002_enable_btree_gist` and `0003_booking_no_overlapping_active_charger_bookings` are critical for booking slot protection.

---

## 6. Verifying Endpoints Through Nginx

Test the reverse proxy and application routes using `curl.exe` or PowerShell's `Invoke-RestMethod`.
*(Note: Use port `8080` by default as defined in `compose.yaml` and `.env.example`, or port `8081` if you configured `NGINX_PORT=8081` in `.env` to resolve a local port conflict).*

```powershell
# Set port variable (defaults to 8080; change to 8081 if overridden)
$PORT = 8080

# 1. Health check probe
curl.exe -i "http://127.0.0.1:$PORT/health/"
# Expected: HTTP/1.1 200 OK -> {"status":"healthy","database":"connected"}

# 2. List stations
curl.exe -i "http://127.0.0.1:$PORT/api/stations/"
# Expected: HTTP/1.1 200 OK -> []

# 3. Register a test driver (using curl.exe with escaped double quotes)
curl.exe -i -X POST "http://127.0.0.1:$PORT/api/auth/register/" `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"testdriver@example.com\",\"username\":\"testdriver\",\"password\":\"StrongPassword123!\"}'
# Expected: HTTP/1.1 201 Created -> {"token":"...","user":{...}}

# Alternative: Register using native PowerShell Invoke-RestMethod
Invoke-RestMethod -Uri "http://127.0.0.1:$PORT/api/auth/register/" -Method Post `
  -ContentType "application/json" `
  -Body (@{ email = "testdriver@example.com"; username = "testdriver"; password = "StrongPassword123!" } | ConvertTo-Json)
```

---

## 7. Running the Test Suite

Execute the complete automated test suite (including unit tests, API tests, and concurrency tests) inside the Docker container:

```powershell
docker compose exec web python manage.py test
```
Expected: `Ran 46 tests in ~11s. OK.`

To run the PostgreSQL concurrency test in isolation with verbose logging:
```powershell
docker compose exec web python manage.py test bookings.tests.PostgresConcurrencyTests -v 2
```

---

## 8. Stopping and Managing Services

### 8.1 Stopping Services Safely
```powershell
docker compose down
```
This halts and removes the containers while **preserving** the database volume (`postgres_data`).

> [!WARNING]
> **NEVER run `docker compose down -v`**.
> The `-v` flag deletes named Docker volumes, which permanently destroys all registered users, vehicles, stations, and booking history.

---

## 9. Troubleshooting Guide

### Issue 1: `bind: address already in use` on Port 8080
- **Cause**: Another host process (such as Jenkins, Java, or an alternative web server) is bound to port `8080`.
- **Solution**: Edit `.env` and set `NGINX_PORT=8081` (or another unused port like `8082`), then run `docker compose up -d`.

### Issue 2: `required variable SECRET_KEY is missing a value: Set SECRET_KEY in .env`
- **Cause**: `.env` file does not exist or lacks `SECRET_KEY`.
- **Solution**: Copy `.env.example` to `.env` and populate a non-empty `SECRET_KEY`.

### Issue 3: Django Web Container Fails to Connect to Database
- **Cause**: Inside Docker Compose, Django must connect to hostname `db`, not `localhost`.
- **Solution**: Verify that `compose.yaml` specifies `DB_HOST: db` and `DB_PORT: "5432"` under the `web` service environment block.

### Issue 4: Local Windows Python Cannot Connect to Database (`psycopg.OperationalError`)
- **Cause**: When running Python directly on the Windows host (outside Docker), `.env` must specify `DB_HOST=127.0.0.1` and `DB_PORT=5433` (do not use `localhost` to avoid Windows IPv6 resolution latency).
