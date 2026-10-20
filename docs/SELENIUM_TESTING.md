# Selenium WebDriver Automated Testing Guide
## EV Charging Slot Booking System (Step 9)

This guide documents the design, test journeys, environment setup, and local execution instructions for the automated Selenium browser test suite.

---

## 1. Overview & Test Architecture

The browser test suite validates end-to-end user workflows against the deployed VoltSlot single-page application and its reverse-proxy gateway (`nginx`).

- **Test Framework**: `pytest` + `selenium` (Python WebDriver)
- **Design Pattern**: Sequential critical journeys with explicit waits (`WebDriverWait` + `expected_conditions`)
- **Browser Compatibility**: Google Chrome (headless or headed) and Microsoft Edge via Selenium Manager (automatic driver management)
- **Test Directory**: [`tests/e2e/`](file:///c:/DevOps_Project/tests/e2e)
- **Artifacts Directory**: [`test-reports/`](file:///c:/DevOps_Project/test-reports) (JUnit XML and failure screenshots)

---

## 2. Tested User Journeys

The suite executes 5 critical user journeys covering the entire application lifecycle:

1. **Journey 1: Driver Registration, Login & Authentication State**
   - Validates unauthenticated landing page state, brand titles, and guest badges.
   - Opens `#auth-modal-dialog`, fills registration fields (`#reg-username`, `#auth-email`, `#auth-password`, `#reg-phone`) with deterministic credentials, and submits.
   - Asserts modal closes, user initials/username appear in the top navigation, user role shows `DRIVER`, `Sign Out` is displayed, and the footer reflects the active session.

2. **Journey 2: Station and Charger Discovery (Live Data & Filters)**
   - Navigates to `Find Stations` via the sidebar.
   - Asserts live stations (`.station-card`) and chargers (`.charger-chip`) loaded from `/api/stations/` and `/api/chargers/`.
   - Tests live search filtering via `.search-bar input` and verifies matching stations update.
   - Tests connector filter pills (`CCS2`, `All Connectors`).

3. **Journey 3: Vehicle Registration (Manage EV Fleet)**
   - Navigates to `My Vehicles` view.
   - Opens `+ Register New EV` modal (`.modal-card`).
   - Fills license plate (`#veh-reg-number`), manufacturer (`#veh-make`), model (`#veh-model`), and battery capacity (`#veh-battery`).
   - Submits form, verifies success banner, and asserts the new vehicle card appears in the active fleet grid.

4. **Journey 4: 30-Minute Slot Reservation / Booking Creation**
   - Navigates to `My Bookings` view.
   - Verifies the newly registered EV is automatically populated in `#slot-vehicle-select`.
   - Selects booking date offset (`Tomorrow`).
   - Waits for live availability intervals, selects the first available 30-minute slot tile (`.slot-tile.available`), and clicks `Reserve 30-Min Slot`.
   - Asserts booking success banner and verifies the new booking card displays status `CONFIRMED` with a `Cancel Slot` action button.

5. **Journey 5: Booking Cancellation & Status Update**
   - Locates the active booking in `My Bookings History`.
   - Clicks `Cancel Slot` and verifies two-step confirmation prompt (`Cancel reservation?` / `Yes, Cancel`).
   - Confirms cancellation and asserts the success alert.
   - Asserts the booking card status updates to `CANCELLED` and the cancel action button is removed.

---

## 3. Prerequisites & Installation

### Prerequisites
- Python 3.10+ in virtual environment `.venv`
- Google Chrome (or Microsoft Edge) installed on host system
- Application running and accessible (e.g. `http://127.0.0.1:8081` via Docker Compose)

### Install Dependencies
Dependencies are defined in [`requirements-test.txt`](file:///c:/DevOps_Project/requirements-test.txt):

```powershell
.\.venv\Scripts\pip.exe install -r requirements-test.txt
```

---

## 4. Configuration & Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `BASE_URL` | `http://127.0.0.1:8081` | HTTP entry point of the deployed Nginx gateway |
| `HEADLESS` | `true` | Set to `false` or `0` to watch tests execute in visible browser window |
| `BROWSER` | `chrome` | Browser driver to instantiate (`chrome` or `edge`) |

---

## 5. Execution Commands

### Run Full Test Suite (Default Headless Mode)
```powershell
.\.venv\Scripts\pytest.exe tests/e2e -v --junitxml=test-reports/junit.xml
```

### Run with Visible Browser (Headed Mode)
```powershell
$env:HEADLESS="false"
.\.venv\Scripts\pytest.exe tests/e2e -v
Remove-Item Env:\HEADLESS
```

### Run Against Custom Port or Host
```powershell
$env:BASE_URL="http://localhost:8085"
.\.venv\Scripts\pytest.exe tests/e2e -v --junitxml=test-reports/junit.xml
Remove-Item Env:\BASE_URL
```

---

## 6. Test Reports & Failure Screenshots

- **JUnit XML Report**: Generated at [`test-reports/junit.xml`](file:///c:/DevOps_Project/test-reports/junit.xml). Compatible with Jenkins JUnit publisher plugin.
- **Automatic Failure Screenshots**: Configured in [`tests/e2e/conftest.py`](file:///c:/DevOps_Project/tests/e2e/conftest.py) via `pytest_runtest_makereport`. If any assertion fails, a full-resolution PNG is saved to:
  `test-reports/screenshots/failure_<test_name>_<timestamp>.png`
- **Git Hygiene**: `test-reports/` is registered in [`.gitignore`](file:///c:/DevOps_Project/.gitignore) to avoid committing binary screenshots or generated test runs.

---

## 7. Continuous Integration (Jenkins Pipeline Integration)

Selenium end-to-end testing is integrated into the Jenkins pipeline defined in [`Jenkinsfile`](file:///c:/DevOps_Project/Jenkinsfile):

1. **Pipeline Ordering**:
   - The isolated smoke deployment (`compose.smoke.yaml`) is built and started on port `8085` with a unique project name `evcharging_smoke_${BUILD_NUMBER}`.
   - Database migrations are applied (`migrate --noinput`).
   - Ephemeral test data is loaded using the seed fixture:
     ```bat
     docker compose -f compose.smoke.yaml -p "%COMPOSE_SMOKE_PROJECT%" exec -T web python manage.py loaddata seed_stations
     ```
   - Production smoke tests run against `http://127.0.0.1:%SMOKE_NGINX_PORT%`.
   - Test dependencies are verified/installed on the host:
     ```bat
     python -m pip install -r requirements-test.txt
     ```
   - The full headless Selenium suite executes against the isolated smoke deployment:
     ```bat
     python -m pytest tests/e2e -v --junitxml=test-reports/junit.xml
     ```
     with `BASE_URL = "http://127.0.0.1:${env.SMOKE_NGINX_PORT}"` and `HEADLESS = "true"`.

2. **Browser & Driver Runtime**:
   - Chrome and matching ChromeDriver paths are prepended to `PATH` in the pipeline `environment` block.
   - Headless Chrome (`--headless=new`, `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`) is utilized.

3. **Report Publishing & Failure Handling**:
   - In `post.always`, the Jenkins `junit` step parses `test-reports/junit.xml` (`allowEmptyResults: true`).
   - `archiveArtifacts` captures any failure screenshots under `test-reports/screenshots/*.png` (`allowEmptyArchive: true`).
   - Any test failure in the Selenium stage aborts the build, preventing downstream deployment or promotion.

4. **Resource Isolation & Teardown**:
   - `post.always` tears down the build-specific smoke stack (`evcharging_smoke_${BUILD_NUMBER}`) and CI stack (`evcharging_ci_${BUILD_NUMBER}`) with `-v --remove-orphans`.
   - Development stack containers, ports (5433, 8081), and development database volume `devops_project_postgres_data` remain untouched.

