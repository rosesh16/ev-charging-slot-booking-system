# Docker Image and Container Lifecycle Guide
## EV Charging Slot Booking System (Step 11)

This document establishes the reproducible Docker image and container lifecycle for the EV Charging Slot Booking System. It covers image building, semantic version tagging, local registry distribution, container startup, port mapping, health checks, log inspection, restart behavior, and teardown.

---

## 1. Architecture & Production Images

The system consists of two primary custom container images plus a managed PostgreSQL database container:

| Service | Dockerfile | Base Image | Role | Default Internal Port |
|---|---|---|---|---|
| **Web (Backend)** | [`Dockerfile`](file:///c:/DevOps_Project/Dockerfile) | `python:3.10-slim` | Django 5.2.18 REST API & Gunicorn application server | `8000` |
| **Nginx (Gateway & Frontend)** | [`nginx/Dockerfile`](file:///c:/DevOps_Project/nginx/Dockerfile) | Multi-stage: `node:22-alpine` & `nginx:alpine` | Static React/Vite asset server & API reverse proxy | `80` |
| **Database** | *Docker Hub* | `postgres:17` | Relational data store | `5432` |

### Key Build Features
- **Backend Non-Root Security**: Uses unprivileged `appuser:appgroup`.
- **Frontend Multi-Stage Efficiency**: Compiles React assets using Node 22 in Stage 1 and serves optimized static assets via Nginx Alpine in Stage 2, resulting in a lightweight ~29 MB production image.
- **Strict Context Isolation**: [`.dockerignore`](file:///c:/DevOps_Project/.dockerignore) strips `.git`, `.venv`, `.env`, and development caches from build contexts.

---

## 2. Image Versioning & Naming Convention

Images follow a semantic versioning and build-traceable naming convention:

```text
<registry-endpoint>/<image-name>:<version>-build<build_number>-<git_short_sha>
<registry-endpoint>/<image-name>:<version>
<registry-endpoint>/<image-name>:latest
```

### Registry Endpoint
- **Local Private Registry**: `127.0.0.1:5000` (Docker Distribution v2 / `registry:2`)
- **Docker Daemon Exemption**: `127.0.0.1:5000` and `localhost:5000` are treated by Docker Desktop as trusted insecure registries without requiring TLS certificate overhead.

### Production Image Identifiers
- `127.0.0.1:5000/ev-charging-slot-booking-web`
- `127.0.0.1:5000/ev-charging-slot-booking-nginx`

---

## 3. Image Lifecycle Commands & Reproduction

### Step 1: Ensure Local Registry is Running
```powershell
# Start local registry on host port 5000 with persistent named storage
docker start devops-registry 2>$null; if ($LASTEXITCODE -ne 0) {
    docker run -d -p 127.0.0.1:5000:5000 --name devops-registry --restart=always -v devops_registry_data:/var/lib/registry registry:2
}

# Verify registry readiness (blocking check with timeout)
python scripts/check_registry.py http://127.0.0.1:5000/v2/_catalog 15
```

#### Registry Storage Architecture & Anonymous Volume Retention Notice
> [!IMPORTANT]
> **Existing Registry Container & Anonymous Volume Storage**:
> - The existing running `devops-registry` container on this host was originally initialized with an **anonymous volume** (volume ID `4c5f5c05ac9f6f8ece4a506e3d264e710f8467f815ab7e1b6a1ca33567af7fbc`) mounted at `/var/lib/registry`.
> - **Preservation Requirement**: The current `devops-registry` container and its associated volume MUST be preserved. Do not run `docker rm -f devops-registry` or `docker volume prune`, as doing so will destroy or orphan the anonymous volume containing all previously published Docker images.
> - **Named Volume Configuration**: The command `docker run ... -v devops_registry_data:/var/lib/registry` configures the named persistent volume `devops_registry_data` for newly provisioned registry containers. However, this named volume is **not automatically attached** to the existing running container.
> - **Data Loss Hazard**: Deleting and recreating `devops-registry` without migrating data will attach a clean, empty `devops_registry_data` volume, immediately losing access to all previously pushed images.
> - **Safe Migration Procedure**:
>   1. Keep reusing the existing container via `docker start devops-registry`.
>   2. To safely migrate image layers to `devops_registry_data` in the future:
>      - Stop `devops-registry`: `docker stop devops-registry`
>      - Create named volume: `docker volume create devops_registry_data`
>      - Copy data from anonymous volume to named volume via a transient helper container:
>        `docker run --rm -v 4c5f5c05ac9f6f8ece4a506e3d264e710f8467f815ab7e1b6a1ca33567af7fbc:/from:ro -v devops_registry_data:/to alpine cp -a /from/. /to/`
>      - Start the new registry container with `-v devops_registry_data:/var/lib/registry`.
>      - Validate the catalog and repositories: `curl.exe http://127.0.0.1:5000/v2/_catalog` and verify tags are pullable.
>      - Only after verification, safely prune or delete the old anonymous volume.
>   3. If migration is not performed, continue reusing the existing container and its active volume.

### Step 2: Build Versioned Production Images
```powershell
$APP_VERSION = "1.0.0"
$BUILD_NUM = "1"
$GIT_SHA = (git rev-parse --short HEAD)
$TAG = "${APP_VERSION}-build${BUILD_NUM}-${GIT_SHA}"

# Build Web Backend Image
docker build -t "127.0.0.1:5000/ev-charging-slot-booking-web:${TAG}" `
             -t "127.0.0.1:5000/ev-charging-slot-booking-web:latest" .

# Build Nginx Gateway & Frontend Image
docker build -f nginx/Dockerfile `
             -t "127.0.0.1:5000/ev-charging-slot-booking-nginx:${TAG}" `
             -t "127.0.0.1:5000/ev-charging-slot-booking-nginx:latest" .
```

### Step 3: Inspect Built Images & Metadata
```powershell
docker images --filter "reference=127.0.0.1:5000/ev-charging-slot-booking-*"
```

**Verified Output Sample:**
```text
REPOSITORY                                      TAG                       IMAGE ID       CREATED          SIZE
127.0.0.1:5000/ev-charging-slot-booking-web     1.0.0-build1-19e4663      be34edf470e9   10 minutes ago   300MB
127.0.0.1:5000/ev-charging-slot-booking-web     latest                    be34edf470e9   10 minutes ago   300MB
127.0.0.1:5000/ev-charging-slot-booking-nginx   1.0.0-build1-19e4663      6cf30e4dd91f   10 minutes ago   103MB
127.0.0.1:5000/ev-charging-slot-booking-nginx   latest                    6cf30e4dd91f   10 minutes ago   103MB
```

### Step 4: Publish to Local Registry
```powershell
docker push "127.0.0.1:5000/ev-charging-slot-booking-web:${TAG}"
docker push "127.0.0.1:5000/ev-charging-slot-booking-web:latest"
docker push "127.0.0.1:5000/ev-charging-slot-booking-nginx:${TAG}"
docker push "127.0.0.1:5000/ev-charging-slot-booking-nginx:latest"

# Query registry repository tags
curl.exe -s http://127.0.0.1:5000/v2/ev-charging-slot-booking-web/tags/list
curl.exe -s http://127.0.0.1:5000/v2/ev-charging-slot-booking-nginx/tags/list
```

### Step 5: Pull Images from Registry
```powershell
docker pull "127.0.0.1:5000/ev-charging-slot-booking-web:${TAG}"
docker pull "127.0.0.1:5000/ev-charging-slot-booking-nginx:${TAG}"
```

---

## 4. Container Deployment & Execution Lifecycle

The deployment configuration is maintained in [`compose.deploy.yaml`](file:///c:/DevOps_Project/compose.deploy.yaml).

### Port & Resource Reservation
| Service | Environment | Host Port | Target Port | Status |
|---|---|---|---|---|
| Jenkins | Host Service | `8080` | `8080` | CI/CD Server |
| Nginx (Development) | `devops_project` | `8081` | `80` | Local Dev Gateway |
| Postgres (Development) | `devops_project` | `5433` | `5432` | Local Dev Database |
| Nginx (CI Smoke Stack) | `evcharging_smoke_${BUILD}` | `8085` | `80` | Ephemeral CI Test Target |
| **Nginx (Production Deployment)** | `evcharging_deploy` | **`8088`** | **`80`** | **Active Production Target** |
| Registry (Local Distribution) | `devops-registry` | `5000` | `5000` | Local Registry |

### Container Lifecycle Commands

#### 1. Start Deployment
```powershell
$env:IMAGE_TAG = "1.0.0-build1-19e4663"
$env:DEPLOY_NGINX_PORT = "8088"
docker compose -f compose.deploy.yaml -p evcharging_deploy up -d --wait
```

#### 2. Apply Migrations & Seed Data
```powershell
docker compose -f compose.deploy.yaml -p evcharging_deploy exec -T web python manage.py migrate --noinput
docker compose -f compose.deploy.yaml -p evcharging_deploy exec -T web python manage.py loaddata seed_stations
```

#### 3. Inspect Container Status & Port Mappings
```powershell
docker compose -f compose.deploy.yaml -p evcharging_deploy ps
```

**Verified Output:**
```text
NAME                    IMAGE                                                                COMMAND                  SERVICE   STATUS                   PORTS
evcharging_deploy-db-1     postgres:17                                                          "docker-entrypoint.s…"   db        Up 1 minute (healthy)    5432/tcp
evcharging_deploy-web-1    127.0.0.1:5000/ev-charging-slot-booking-web:1.0.0-build1-19e4663     "gunicorn --bind 0.0…"   web       Up 1 minute (healthy)    8000/tcp
evcharging_deploy-nginx-1  127.0.0.1:5000/ev-charging-slot-booking-nginx:1.0.0-build1-19e4663   "/docker-entrypoint.…"   nginx     Up 1 minute              127.0.0.1:8088->80/tcp
```

#### 4. Verify Health Checks & Endpoints
```powershell
# Run full automated deployment smoke test suite
python scripts/smoke_test.py --base-url "http://127.0.0.1:8088"
```
*Result: 7/7 checks passed (Frontend 200, static JS/CSS 200, SPA routing 200, Health 200, Stations API 200, Chargers API 200, 404 API handling).*

#### 5. Inspect Container Logs
```powershell
docker compose -f compose.deploy.yaml -p evcharging_deploy logs --tail 50
```

#### 6. Stop and Restart Verification
```powershell
# Stop services safely
docker compose -f compose.deploy.yaml -p evcharging_deploy stop

# Restart services
docker compose -f compose.deploy.yaml -p evcharging_deploy start
```

#### 7. Clean Removal (When Replaced or Decommissioned)
```powershell
docker compose -f compose.deploy.yaml -p evcharging_deploy down -v --remove-orphans
```

---

## 5. Development Isolation Safety Guarantee

All commands and configurations strictly isolate:
- The persistent development PostgreSQL volume `devops_project_postgres_data` is untouched.
- Development containers `devops_project-web-1`, `devops_project-nginx-1` (port 8081), and `devops_project-db-1` (port 5433) are never stopped, re-created, or modified.
- Ephemeral test projects use project scopes `evcharging_ci_*`, `evcharging_smoke_*`, and `test_lifecycle_*`.
