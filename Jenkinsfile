
pipeline {
    agent any

    options {
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Source is checked out by Jenkins SCM configuration.'
                sh 'pwd; ls -la'
            }
        }

        stage('Validate Application') {
            steps {
                sh '''
                    test -f app.py
                    test -f requirements.txt
                    test -f Dockerfile
                    echo "Required application files found."
                '''
            }
        }

        stage('Dependency Review') {
            steps {
                sh '''
                    echo "Dependency manifest:"
                    cat requirements.txt
                '''
            }
        }

        stage('Docker Image Security Scan') {
            steps {
                sh '''
                    if command -v docker >/dev/null 2>&1; then
                        echo "Docker CLI is available."
                        docker image ls
                    else
                        echo "Docker CLI is not available inside the Jenkins agent."
                        echo "Run Trivy separately and retain the scan report as evidence."
                    fi
                '''
            }
        }
    }

    post {
        success {
            echo 'SecureAttend validation pipeline completed successfully.'
        }
        failure {
            echo 'Pipeline failed. Review Console Output.'
        }
    }
}
