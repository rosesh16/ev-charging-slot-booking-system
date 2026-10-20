pipeline {
    agent any

    options {
        timeout(time: 15, unit: 'MINUTES')
        timestamps()
    }

    environment {
        // Prepend Chrome, ChromeDriver, Python scripts, and Docker Desktop binary directories for Windows service execution
        PATH = "C:\\Program Files\\Google\\Chrome\\Application;C:\\ProgramData\\selenium\\chromedriver;C:\\Users\\ASUS\\AppData\\Local\\Programs\\Python\\Python310\\Scripts;C:\\Users\\ASUS\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin;${env.PATH}"
        DOCKER_CONFIG = "C:\\Users\\ASUS\\.docker"
        REGISTRY_HOST = '127.0.0.1:5000'
        IMAGE_NAME_WEB = 'ev-charging-slot-booking-web'
        IMAGE_NAME_NGINX = 'ev-charging-slot-booking-nginx'
        APP_VERSION = '1.0.0'
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

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    def shortSha = bat(script: '@git rev-parse --short HEAD', returnStdout: true)?.trim()
                    def fullSha = bat(script: '@git rev-parse HEAD', returnStdout: true)?.trim()
                    if (!shortSha || !fullSha || shortSha.startsWith('fatal')) {
                        error "Unable to resolve Git commit SHA for immutable image tagging."
                    }
                    env.GIT_COMMIT_SHORT = shortSha
                    env.GIT_COMMIT_FULL = fullSha
                    env.IMAGE_TAG = "${env.APP_VERSION}-build${env.BUILD_NUMBER}-${shortSha}"
                    echo "Configured immutable release image tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Validate Docker Environment') {
            steps {
                bat 'docker version'
                bat 'docker compose version'
                bat 'docker start devops-registry 2>nul || docker run -d -p 127.0.0.1:5000:5000 --name devops-registry --restart=always -v devops_registry_data:/var/lib/registry registry:2'
                bat 'python scripts/check_registry.py http://127.0.0.1:5000/v2/_catalog 15'
            }
        }

        stage('Frontend Dependencies') {
            steps {
                bat 'npm --prefix frontend ci'
            }
        }

        stage('Frontend Lint') {
            steps {
                bat 'npm --prefix frontend run lint'
            }
        }

        stage('Frontend Build') {
            steps {
                bat 'npm --prefix frontend run build'
            }
        }

        stage('Build Production Images') {
            steps {
                bat 'docker build -t "%REGISTRY_HOST%/%IMAGE_NAME_WEB%:%IMAGE_TAG%" -t "%REGISTRY_HOST%/%IMAGE_NAME_WEB%:latest" .'
                bat 'docker build -f nginx/Dockerfile -t "%REGISTRY_HOST%/%IMAGE_NAME_NGINX%:%IMAGE_TAG%" -t "%REGISTRY_HOST%/%IMAGE_NAME_NGINX%:latest" -t ev-charging-slot-booking-nginx:ci .'
            }
        }

        stage('Build CI Images') {
            steps {
                bat 'docker compose -f compose.ci.yaml -p "%COMPOSE_PROJECT_NAME%" build'
            }
        }

        stage('Start Database & Wait for Readiness') {
            steps {
                bat 'docker compose -f compose.ci.yaml -p "%COMPOSE_PROJECT_NAME%" up -d --wait db'
            }
        }

        stage('Django System Checks') {
            steps {
                bat 'docker compose -f compose.ci.yaml -p "%COMPOSE_PROJECT_NAME%" run --rm web python manage.py check'
            }
        }

        stage('Verify Migrations') {
            steps {
                bat 'docker compose -f compose.ci.yaml -p "%COMPOSE_PROJECT_NAME%" run --rm web python manage.py makemigrations --check --dry-run'
            }
        }

        stage('Run Automated Tests') {
            steps {
                bat 'docker compose -f compose.ci.yaml -p "%COMPOSE_PROJECT_NAME%" run --rm web python manage.py test --noinput --verbosity=2'
            }
        }

        stage('Build Smoke Images') {
            steps {
                bat 'docker compose -f compose.smoke.yaml -p "%COMPOSE_SMOKE_PROJECT%" build'
            }
        }

        stage('Start Smoke Deployment') {
            steps {
                bat 'docker compose -f compose.smoke.yaml -p "%COMPOSE_SMOKE_PROJECT%" up -d --wait'
            }
        }

        stage('Apply Smoke Database Migrations') {
            steps {
                bat 'docker compose -f compose.smoke.yaml -p "%COMPOSE_SMOKE_PROJECT%" exec -T web python manage.py migrate --noinput'
            }
        }

        stage('Seed Smoke Database') {
            steps {
                bat 'docker compose -f compose.smoke.yaml -p "%COMPOSE_SMOKE_PROJECT%" exec -T web python manage.py loaddata seed_stations'
            }
        }

        stage('Run Production Smoke Tests') {
            steps {
                bat 'python scripts/smoke_test.py --base-url "http://127.0.0.1:%SMOKE_NGINX_PORT%"'
            }
        }

        stage('Selenium Test Dependencies') {
            steps {
                bat 'python -m pip install -r requirements-test.txt'
            }
        }

        stage('Run Selenium E2E Tests') {
            environment {
                BASE_URL = "http://127.0.0.1:${env.SMOKE_NGINX_PORT}"
                HEADLESS = 'true'
            }
            steps {
                bat 'python -m pytest tests/e2e -v --junitxml=test-reports/junit.xml'
            }
        }

        stage('Publish Versioned Images') {
            steps {
                bat 'docker push "%REGISTRY_HOST%/%IMAGE_NAME_WEB%:%IMAGE_TAG%"'
                bat 'docker push "%REGISTRY_HOST%/%IMAGE_NAME_WEB%:latest"'
                bat 'docker push "%REGISTRY_HOST%/%IMAGE_NAME_NGINX%:%IMAGE_TAG%"'
                bat 'docker push "%REGISTRY_HOST%/%IMAGE_NAME_NGINX%:latest"'
            }
        }

        stage('Deploy to Isolated Target') {
            steps {
                script {
                    bat "if not exist \"${env.DEPLOY_STATE_DIR}\" mkdir \"${env.DEPLOY_STATE_DIR}\""

                    def currentTagFile = "${env.DEPLOY_STATE_DIR}\\current_tag.txt"
                    def previousTag = ""
                    if (fileExists(currentTagFile)) {
                        previousTag = readFile(currentTagFile).trim()
                        if (previousTag) {
                            writeFile file: "${env.DEPLOY_STATE_DIR}\\previous_tag.txt", text: previousTag
                            echo "Preserved previous known-good deployment tag: ${previousTag}"
                        }
                    } else {
                        echo "No previous deployment tag found. This is the initial deployment."
                    }
                    env.PREVIOUS_DEPLOY_TAG = previousTag

                    try {
                        echo "Deploying immutable image tag: ${env.IMAGE_TAG} to port ${env.DEPLOY_NGINX_PORT}..."
                        bat """
                            set IMAGE_TAG=${env.IMAGE_TAG}
                            set DEPLOY_NGINX_PORT=${env.DEPLOY_NGINX_PORT}
                            docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" pull
                            docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" up -d --wait
                            docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" exec -T web python manage.py migrate --noinput
                            docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" exec -T web python manage.py loaddata seed_stations
                        """
                    } catch (deployErr) {
                        rollbackDeployment(env.PREVIOUS_DEPLOY_TAG, env.DEPLOY_NGINX_PORT, env.COMPOSE_DEPLOY_PROJECT, deployErr)
                    }
                }
            }
        }

        stage('Verify Deployment Health') {
            steps {
                script {
                    try {
                        echo "Verifying deployment health at http://127.0.0.1:${env.DEPLOY_NGINX_PORT}..."
                        bat "python scripts/smoke_test.py --base-url \"http://127.0.0.1:${env.DEPLOY_NGINX_PORT}\""
                    } catch (healthErr) {
                        rollbackDeployment(env.PREVIOUS_DEPLOY_TAG, env.DEPLOY_NGINX_PORT, env.COMPOSE_DEPLOY_PROJECT, healthErr)
                    }
                }
            }
        }

        stage('Record Deployment Metadata') {
            steps {
                script {
                    writeFile file: "${env.DEPLOY_STATE_DIR}\\current_tag.txt", text: env.IMAGE_TAG

                    def nowUtc = new Date().format("yyyy-MM-dd'T'HH:mm:ss'Z'", TimeZone.getTimeZone('UTC'))
                    def manifestContent = """{
  "build_number": "${env.BUILD_NUMBER}",
  "git_commit_full": "${env.GIT_COMMIT_FULL}",
  "git_commit_short": "${env.GIT_COMMIT_SHORT}",
  "image_tag": "${env.IMAGE_TAG}",
  "backend_image": "${env.REGISTRY_HOST}/${env.IMAGE_NAME_WEB}:${env.IMAGE_TAG}",
  "nginx_image": "${env.REGISTRY_HOST}/${env.IMAGE_NAME_NGINX}:${env.IMAGE_TAG}",
  "registry_endpoint": "${env.REGISTRY_HOST}",
  "deployment_port": "${env.DEPLOY_NGINX_PORT}",
  "deployment_status": "HEALTHY",
  "deployed_at": "${nowUtc}"
}"""
                    writeFile file: "${env.DEPLOY_STATE_DIR}\\deployment-manifest.json", text: manifestContent

                    if (!fileExists('deployments')) {
                        bat 'if not exist "deployments" mkdir deployments'
                    }
                    writeFile file: "deployments\\current_tag.txt", text: env.IMAGE_TAG
                    writeFile file: "deployments\\deployment-manifest.json", text: manifestContent
                    if (env.PREVIOUS_DEPLOY_TAG) {
                        writeFile file: "deployments\\previous_tag.txt", text: env.PREVIOUS_DEPLOY_TAG
                    }
                    echo "Recorded deployment metadata for tag ${env.IMAGE_TAG}."
                }
            }
        }
    }

    post {
        failure {
            script {
                echo "=== DUMPING LOGS ON FAILURE ==="
                try {
                    bat 'docker compose -f compose.smoke.yaml -p "%COMPOSE_SMOKE_PROJECT%" logs --tail 100'
                } catch (logErr) {
                    echo "Could not collect smoke logs: ${logErr}"
                }
                try {
                    bat 'docker compose -f compose.deploy.yaml -p "%COMPOSE_DEPLOY_PROJECT%" logs --tail 100'
                } catch (deployErr) {
                    echo "Could not collect deploy logs: ${deployErr}"
                }
            }
        }
        always {
            script {
                try {
                    junit testResults: 'test-reports/junit.xml', allowEmptyResults: true
                } catch (reportErr) {
                    echo "Could not publish JUnit test results: ${reportErr}"
                }

                try {
                    archiveArtifacts artifacts: 'test-reports/screenshots/*.png', allowEmptyArchive: true
                } catch (archiveErr) {
                    echo "Could not archive screenshots: ${archiveErr}"
                }

                try {
                    archiveArtifacts artifacts: 'deployments/*', allowEmptyArchive: true
                } catch (manifestErr) {
                    echo "Could not archive deployment manifest: ${manifestErr}"
                }

                def teardownError = null
                try {
                    bat 'docker compose -f compose.smoke.yaml -p "%COMPOSE_SMOKE_PROJECT%" down -v --remove-orphans'
                } catch (err) {
                    echo "Teardown failed for smoke project ${env.COMPOSE_SMOKE_PROJECT}: ${err}"
                    teardownError = err
                }

                try {
                    bat 'docker compose -f compose.ci.yaml -p "%COMPOSE_PROJECT_NAME%" down -v --remove-orphans'
                } catch (err) {
                    echo "Teardown failed for CI project ${env.COMPOSE_PROJECT_NAME}: ${err}"
                    if (!teardownError) {
                        teardownError = err
                    }
                } finally {
                    cleanWs()
                }

                if (teardownError) {
                    throw teardownError
                }
            }
        }
    }
}

def rollbackDeployment(String prevTag, String deployPort, String composeProject, Throwable originalErr) {
    echo "=== DEPLOYMENT FAILURE DETECTED ==="
    echo "Failure cause: ${originalErr.message}"
    if (prevTag && prevTag.trim() != "") {
        echo "Initiating automatic rollback to previous known-good tag: ${prevTag}..."
        try {
            bat """
                set IMAGE_TAG=${prevTag}
                set DEPLOY_NGINX_PORT=${deployPort}
                docker compose -f compose.deploy.yaml -p "${composeProject}" up -d --wait
                python scripts/smoke_test.py --base-url "http://127.0.0.1:${deployPort}"
            """
            echo "[ROLLBACK SUCCESSFUL] Restored and verified previous known-good deployment: ${prevTag}"
        } catch (rollbackErr) {
            echo "[ROLLBACK FAILED] Automated rollback to ${prevTag} encountered an error: ${rollbackErr}"
        }
    } else {
        echo "[ROLLBACK UNAVAILABLE] First deployment; no previous known-good tag exists to restore."
    }
    throw originalErr
}
