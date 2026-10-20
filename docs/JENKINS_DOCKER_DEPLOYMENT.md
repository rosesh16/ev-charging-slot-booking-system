# Jenkins Continuous Deployment to Docker Containers
## EV Charging Slot Booking System (Step 12)

This document details the continuous deployment (CD) pipeline integrated into Jenkins via [`Jenkinsfile`](file:///c:/DevOps_Project/Jenkinsfile). It documents the commit-to-container workflow, versioned image publishing, deployment gate verification, health validation, rollback strategy, and resource isolation.

---

## 1. Continuous Deployment Pipeline Architecture

The pipeline enforces a strict quality gate: **images are only built with release tags, published to the registry, and deployed after 100% of frontend, backend, migration, smoke, and Selenium end-to-end tests succeed.**

```
+---------------------------------------------------------------------------------------------------+
|                                  STAGE 1: CODE & STATIC VALIDATION                                |
|  Checkout -> Docker Validation -> Frontend Dependencies -> Frontend Lint -> Frontend Build       |
+---------------------------------------------------------------------------------------------------+
                                                  |
+---------------------------------------------------------------------------------------------------+
|                                  STAGE 2: ISOLATED CI VERIFICATION                                |
|  Build CI Images -> Start Isolated DB -> Django Checks -> Verify Migrations -> 62 Backend Tests   |
+---------------------------------------------------------------------------------------------------+
                                                  |
+---------------------------------------------------------------------------------------------------+
|                             STAGE 3: PRE-DEPLOYMENT SMOKE & E2E TESTING                           |
|  Build Smoke Images -> Start Smoke Deployment (Port 8085) -> Migrate -> Seed Stations             |
|  -> Run Smoke Tests (7 checks) -> Install Selenium Deps -> Run 5 Selenium User Journeys (Headless)|
+---------------------------------------------------------------------------------------------------+
                                                  |
                                    [STRICT DEPLOYMENT GATE]
                   (Any test failure aborts pipeline; no publish or deploy)
                                                  |
+---------------------------------------------------------------------------------------------------+
|                                 STAGE 4: PUBLISH VERSIONED IMAGES                                 |
|  Build Version-Tagged Production Images -> Push to Registry (127.0.0.1:5000)                      |
+---------------------------------------------------------------------------------------------------+
                                                  |
+---------------------------------------------------------------------------------------------------+
|                                 STAGE 5: CONTINUOUS DEPLOYMENT                                    |
|  Save Previous Tag -> Pull Versioned Images -> Deploy (Port 8088) -> Migrate -> Seed Stations     |
+---------------------------------------------------------------------------------------------------+
                                                  |
+---------------------------------------------------------------------------------------------------+
|                            STAGE 6: POST-DEPLOYMENT HEALTH VERIFICATION                           |
|  Run Smoke Tests against Port 8088 -> Record Deployment Metadata Artifact (deployment-manifest.json)|
+---------------------------------------------------------------------------------------------------+
                                                  |
+---------------------------------------------------------------------------------------------------+
|                                    POST ACTIONS & TEARDOWN                                        |
|  Publish JUnit XML -> Archive Screenshots -> Teardown Ephemeral CI & Smoke Stacks -> Clean Workspace|
|  (Note: Production Deployment on Port 8088 remains running!)                                      |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Pipeline Configuration & Environment Variables

Configured in [`Jenkinsfile`](file:///c:/DevOps_Project/Jenkinsfile):

```groovy
environment {
    PATH = "C:\\Program Files\\Google\\Chrome\\Application;C:\\ProgramData\\selenium\\chromedriver;C:\\Users\\ASUS\\AppData\\Local\\Programs\\Python\\Python310\\Scripts;C:\\Users\\ASUS\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin;${env.PATH}"
    DOCKER_CONFIG = "C:\\Users\\ASUS\\.docker"
    REGISTRY_HOST = '127.0.0.1:5000'
    APP_VERSION = '1.0.0'
    IMAGE_NAME_WEB = 'ev-charging-slot-booking-web'
    IMAGE_NAME_NGINX = 'ev-charging-slot-booking-nginx'
    DEPLOY_STATE_DIR = 'C:\\ProgramData\\Jenkins\\.jenkins\\deployments\\ev-charging-slot-booking'
    COMPOSE_PROJECT_NAME = "evcharging_ci_${BUILD_NUMBER}"
    COMPOSE_SMOKE_PROJECT = "evcharging_smoke_${BUILD_NUMBER}"
    COMPOSE_DEPLOY_PROJECT = 'evcharging_deploy'
    SMOKE_NGINX_PORT = '8085'
    DEPLOY_NGINX_PORT = '8088'
    POSTGRES_DB = 'ci_evcharging'
    POSTGRES_USER = 'ci_evapp'
    POSTGRES_PASSWORD = 'ci_secret_test_password'
    SECRET_KEY = 'ci-ephemeral-dummy-key-not-for-production-use-39281729'
    DEBUG = '0'
}
```

---

## 3. Deployment Stages in Detail

### Stage 1: Checkout & Immutable Git SHA Resolution
Directly after `checkout scm`, the pipeline extracts the full and short Git commit SHAs using `git rev-parse`. If unavailable or invalid, the pipeline halts immediately to prevent deploying an untraceable image:
```groovy
env.GIT_COMMIT_SHORT = bat(script: '@git rev-parse --short HEAD', returnStdout: true)?.trim()
env.GIT_COMMIT_FULL  = bat(script: '@git rev-parse HEAD', returnStdout: true)?.trim()
env.IMAGE_TAG = "${env.APP_VERSION}-build${env.BUILD_NUMBER}-${shortSha}"
```

### Stage 2: Validate Docker & Registry Readiness
Reuses the active local Docker registry or starts a new instance with persistent named storage, followed by a blocking HTTP readiness poll with timeout:
```bat
docker start devops-registry 2>nul || docker run -d -p 127.0.0.1:5000:5000 --name devops-registry --restart=always -v devops_registry_data:/var/lib/registry registry:2
python scripts/check_registry.py http://127.0.0.1:5000/v2/_catalog 15
```
*(Note: As detailed in `docs/DOCKER_LIFECYCLE.md`, the existing host registry uses an anonymous volume that is preserved by `docker start`; the named volume `devops_registry_data` applies to freshly initialized containers. Never recreate the container without data migration.)*

### Stage 3: Build Versioned Production Images
Builds both images with the immutable tag:
```bat
docker build -t "%REGISTRY_HOST%/%IMAGE_NAME_WEB%:%IMAGE_TAG%" -t "%REGISTRY_HOST%/%IMAGE_NAME_WEB%:latest" .
docker build -f nginx/Dockerfile -t "%REGISTRY_HOST%/%IMAGE_NAME_NGINX%:%IMAGE_TAG%" -t "%REGISTRY_HOST%/%IMAGE_NAME_NGINX%:latest" -t ev-charging-slot-booking-nginx:ci .
```

### Stage 4: Publish to Local Docker Registry
Only executes after all backend tests, migration checks, smoke tests, and Selenium E2E tests have passed 100%:
```bat
docker push "%REGISTRY_HOST%/%IMAGE_NAME_WEB%:%IMAGE_TAG%"
docker push "%REGISTRY_HOST%/%IMAGE_NAME_WEB%:latest"
docker push "%REGISTRY_HOST%/%IMAGE_NAME_NGINX%:%IMAGE_TAG%"
docker push "%REGISTRY_HOST%/%IMAGE_NAME_NGINX%:latest"
```

### Stage 5: Deploy to Isolated Target (`compose.deploy.yaml`)
1. **Persistent History Preservation**: Reads the current tag from `C:\ProgramData\Jenkins\.jenkins\deployments\ev-charging-slot-booking\current_tag.txt` (if present) and stores it as `previous_tag.txt`. If no previous tag exists (first deployment), it records that no prior tag is available.
2. **Pull and Deploy with Rollback Guard**:
   ```bat
   set IMAGE_TAG=%IMAGE_TAG%
   set DEPLOY_NGINX_PORT=%DEPLOY_NGINX_PORT%
   docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" pull
   docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" up -d --wait
   docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" exec -T web python manage.py migrate --noinput
   docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" exec -T web python manage.py loaddata seed_stations
   ```
   If any command fails (image pull, container startup, migration, seed), the stage catches the failure and immediately triggers the unified `rollbackDeployment` procedure.

### Stage 6: Post-Deployment Verification & Automated Rollback
Runs live smoke tests against the active deployment target (`http://127.0.0.1:8088`):
```bat
python scripts/smoke_test.py --base-url "http://127.0.0.1:%DEPLOY_NGINX_PORT%"
```
- **If Verification Passes**: Stage 7 updates `current_tag.txt` and records `deployment-manifest.json`.
- **If Verification Fails**: The stage catches the failure and triggers the unified `rollbackDeployment` procedure.

### Stage 7: Record Deployment Metadata
Saves structured metadata into persistent storage and copies to the workspace for artifact archiving:
```json
{
  "build_number": "8",
  "git_commit_full": "19e4663c04d94ccf63cbed5434e8e56f181aa025",
  "git_commit_short": "19e4663",
  "image_tag": "1.0.0-build8-19e4663",
  "backend_image": "127.0.0.1:5000/ev-charging-slot-booking-web:1.0.0-build8-19e4663",
  "nginx_image": "127.0.0.1:5000/ev-charging-slot-booking-nginx:1.0.0-build8-19e4663",
  "registry_endpoint": "127.0.0.1:5000",
  "deployment_port": "8088",
  "deployment_status": "HEALTHY",
  "deployed_at": "2026-10-20T09:14:00Z"
}
```

---

## 4. Rollback Strategy & Verification

### Unified Pipeline Rollback Procedure (`rollbackDeployment`)
Implemented as a centralized pipeline helper shared across deployment and health verification:
- **Comprehensive Failure Scope**: Covers image pull, container startup (`docker compose up`), database migrations, database seeding, and post-deployment smoke tests.
- **Rollback Execution**:
  - Checks if `PREVIOUS_DEPLOY_TAG` exists.
  - If present: Executes `docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" up -d --wait` with `IMAGE_TAG` set to the previous known-good tag, then runs `smoke_test.py` against port 8088.
  - Logs `[ROLLBACK SUCCESSFUL]` or `[ROLLBACK FAILED]`.
  - If no previous tag exists: Logs `[ROLLBACK UNAVAILABLE] First deployment; no previous known-good tag exists to restore.`
  - In all cases, rethrows the original deployment error to fail the Jenkins build without masking root causes.
- **State Protection**: `current_tag.txt` and `deployment-manifest.json` are never modified on failure.

### Manual Rollback Procedure
```powershell
# 1. Read the verified previous tag from persistent storage
$ROLLBACK_TAG = (Get-Content "C:\ProgramData\Jenkins\.jenkins\deployments\ev-charging-slot-booking\previous_tag.txt")

# 2. Redeploy the verified tag
$env:IMAGE_TAG = $ROLLBACK_TAG
$env:DEPLOY_NGINX_PORT = "8088"
docker compose -f compose.deploy.yaml -p evcharging_deploy up -d --wait

# 3. Verify health
python scripts/smoke_test.py --base-url "http://127.0.0.1:8088"
```

---

## 5. Teardown & Environment Safety Rules

- **Ephemeral CI Stack** (`evcharging_ci_${BUILD_NUMBER}`): Torn down in `post.always`.
- **Ephemeral Smoke Stack** (`evcharging_smoke_${BUILD_NUMBER}`): Torn down in `post.always`.
- **Active Deployment Stack** (`evcharging_deploy` on port 8088): Remains running as the active deployed application.
- **Development Stack** (`devops_project` on ports 8081 & 5433): Strictly preserved; never modified, stopped, or targeted.
- **Database Volume Safety**: `devops_project_postgres_data` is untouched.

