pipeline {
    agent any

    options {
        timeout(time: 15, unit: 'MINUTES')
        timestamps()
    }

    environment {
        // Prepend Docker Desktop binary directory for Windows service execution
        PATH = "C:\\Users\\ASUS\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin;${env.PATH}"
        DOCKER_CONFIG = "C:\\Users\\ASUS\\.docker"
        COMPOSE_PROJECT_NAME = "evcharging_ci_${BUILD_NUMBER}"
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
    }

    post {
        always {
            script {
                try {
                    bat 'docker compose -f compose.ci.yaml -p "%COMPOSE_PROJECT_NAME%" down -v --remove-orphans'
                } catch (err) {
                    echo "Teardown failed for Compose project ${env.COMPOSE_PROJECT_NAME}: ${err}"
                    throw err
                } finally {
                    cleanWs()
                }
            }
        }
    }
}
