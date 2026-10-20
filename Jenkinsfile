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
        COMPOSE_PROJECT_NAME = "evcharging_ci_${BUILD_NUMBER}"
        COMPOSE_SMOKE_PROJECT = "evcharging_smoke_${BUILD_NUMBER}"
        SMOKE_NGINX_PORT = '8085'
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
            }
        }

        stage('Validate Docker Environment') {
            steps {
                bat 'docker version'
                bat 'docker compose version'
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

        stage('Build Production Nginx Image') {
            steps {
                bat 'docker build -f nginx/Dockerfile -t ev-charging-slot-booking-nginx:ci .'
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
    }

    post {
        failure {
            script {
                echo "=== DUMPING SMOKE TEST CONTAINER LOGS ON FAILURE ==="
                try {
                    bat 'docker compose -f compose.smoke.yaml -p "%COMPOSE_SMOKE_PROJECT%" logs --tail 100'
                } catch (logErr) {
                    echo "Could not collect smoke logs: ${logErr}"
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
