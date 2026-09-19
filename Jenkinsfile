pipeline {
    agent any

    environment {
        APP_NAME = "face-attendance-app"
        IMAGE_TAG = "build-${BUILD_NUMBER}"
        PORT = "5000"
    }

    stages {
        stage('Checkout Code') {
            steps {
                echo 'Checking out source code from GitHub...'
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building Docker container image...'
                sh "docker build -t ${APP_NAME}:${IMAGE_TAG} -t ${APP_NAME}:latest ."
            }
        }

        stage('Run Automated Tests inside Container') {
            steps {
                echo 'Running unit & integration tests inside container...'
                sh "docker run --rm ${APP_NAME}:${IMAGE_TAG} python -m pytest"
            }
        }

        stage('Container Health Verification') {
            steps {
                echo 'Testing Docker container health endpoint...'
                sh """
                    docker stop test_health_check || true
                    docker rm test_health_check || true
                    docker run -d --name test_health_check ${APP_NAME}:${IMAGE_TAG}
                    sleep 3
                    docker exec test_health_check python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1
                    docker stop test_health_check
                    docker rm test_health_check
                """
            }
        }

        stage('Deploy Production Container') {
            steps {
                echo 'Deploying containerized application...'
                sh """
                    docker stop ${APP_NAME}_running || true
                    docker rm ${APP_NAME}_running || true
                    docker stop attendance_container || true
                    docker rm attendance_container || true
                    docker run -d \\
                        --name ${APP_NAME}_running \\
                        -p ${PORT}:5000 \\
                        -v attendance_db:/app/app/data \\
                        -v student_faces:/app/app/student_faces \\
                        --restart always \\
                        ${APP_NAME}:latest
                """
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline execution completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed! Check logs for details.'
        }
    }
}
