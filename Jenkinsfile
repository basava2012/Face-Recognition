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

        stage('Install Dependencies') {
            steps {
                echo 'Setting up Python virtual environment & installing dependencies...'
                sh '''
                    python3 -m venv venv || python -m venv venv
                    . venv/bin/activate || . venv/Scripts/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Automated Tests') {
            steps {
                echo 'Running unit & integration test suite with pytest...'
                sh '''
                    . venv/bin/activate || . venv/Scripts/activate
                    pytest --junitxml=test-results.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results.xml'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building Docker container image...'
                sh "docker build -t ${APP_NAME}:${IMAGE_TAG} -t ${APP_NAME}:latest ."
            }
        }

        stage('Container Health Verification') {
            steps {
                echo 'Testing Docker container health endpoint...'
                sh """
                    docker stop test_health_check || true
                    docker rm test_health_check || true
                    docker run -d --name test_health_check -p 5001:5000 ${APP_NAME}:${IMAGE_TAG}
                    sleep 5
                    curl -f http://localhost:5001/health || exit 1
                    docker stop test_health_check
                    docker rm test_health_check
                """
            }
        }

        stage('Deploy to Production') {
            steps {
                echo 'Deploying containerized application...'
                // For local deployment or EC2 deployment script:
                sh """
                    docker stop ${APP_NAME}_running || true
                    docker rm ${APP_NAME}_running || true
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
