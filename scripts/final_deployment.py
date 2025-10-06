# scripts/final_deployment.py
# !/usr/bin/env python3
"""
Final Deployment Script for Business Scraper
This script handles the complete production deployment process
"""

import os
import sys
import subprocess
import requests
import time
import json
from datetime import datetime


class FinalDeployment:
    def __init__(self):
        self.deployment_log = []
        self.start_time = datetime.now()

    def log(self, message, level='INFO'):
        """Log deployment messages"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}"
        self.deployment_log.append(log_entry)
        print(log_entry)

    def run_command(self, command, check=True):
        """Run a shell command"""
        self.log(f"Running: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                check=check,
                capture_output=True,
                text=True
            )

            if result.stdout:
                self.log(f"Output: {result.stdout.strip()}")

            return result.returncode == 0

        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", 'ERROR')
            if e.stderr:
                self.log(f"Error output: {e.stderr.strip()}", 'ERROR')
            return False

    def check_prerequisites(self):
        """Check system prerequisites"""
        self.log("Checking deployment prerequisites...")

        prerequisites = [
            ('Docker', 'docker --version'),
            ('Docker Compose', 'docker-compose --version'),
            ('Git', 'git --version'),
            ('Python', 'python3 --version')
        ]

        all_ok = True
        for name, command in prerequisites:
            if self.run_command(command, check=False):
                self.log(f"✓ {name} is installed")
            else:
                self.log(f"✗ {name} is not installed", 'ERROR')
                all_ok = False

        return all_ok

    def load_environment(self):
        """Load environment variables"""
        self.log("Loading environment configuration...")

        if not os.path.exists('.env.production'):
            self.log("Creating default .env.production file", 'WARNING')
            self.create_default_env_file()

        # Load environment variables
        with open('.env.production', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

        self.log("Environment configuration loaded")

    def create_default_env_file(self):
        """Create default environment file"""
        default_env = """# Database Configuration
DB_NAME=business_scraper
DB_USER=scraper
DB_PASSWORD=change_this_password
DATABASE_URL=postgresql://scraper:change_this_password@db:5432/business_scraper

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Flask Configuration
SECRET_KEY=change_this_to_a_secure_secret_key
FLASK_ENV=production

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password

# Scraping Configuration
MAX_CONCURRENT_SCRAPERS=3
REQUEST_TIMEOUT=30
MAX_RESULTS=100
"""

        with open('.env.production', 'w') as f:
            f.write(default_env)

    def run_security_scan(self):
        """Run security scan"""
        self.log("Running security scan...")

        # Check for common security issues
        security_checks = [
            ("Default secret key", os.getenv('SECRET_KEY') == 'change_this_to_a_secure_secret_key'),
            ("Default database password", os.getenv('DB_PASSWORD') == 'change_this_password'),
            ("Debug mode enabled", os.getenv('FLASK_DEBUG') == '1'),
        ]

        security_issues = []
        for check_name, is_vulnerable in security_checks:
            if is_vulnerable:
                security_issues.append(check_name)
                self.log(f"Security issue: {check_name}", 'WARNING')
            else:
                self.log(f"✓ {check_name} - OK")

        if security_issues:
            self.log(f"Found {len(security_issues)} security issues that should be addressed", 'WARNING')

        return len(security_issues) == 0

    def build_and_deploy(self):
        """Build and deploy the application"""
        self.log("Starting application build and deployment...")

        steps = [
            ("Stopping existing containers", "docker-compose down"),
            ("Building new images", "docker-compose build --no-cache"),
            ("Starting services", "docker-compose up -d"),
            ("Waiting for services to be ready", "sleep 30"),
            ("Running database migrations", "docker-compose exec web flask db upgrade"),
            ("Creating database tables", "docker-compose exec web python -c \"from app import db; db.create_all()\""),
        ]

        for step_name, command in steps:
            self.log(f"Step: {step_name}")
            if not self.run_command(command):
                self.log(f"Deployment failed at step: {step_name}", 'ERROR')
                return False
            time.sleep(5)  # Brief pause between steps

        self.log("Application deployment completed successfully")
        return True

    def run_health_checks(self):
        """Run comprehensive health checks"""
        self.log("Running post-deployment health checks...")

        health_checks = [
            ("Web application", "http://localhost:5000/health"),
            ("API endpoints", "http://localhost:5000/api/v1/health"),
            ("Database connectivity", "docker-compose exec db pg_isready -U scraper -d business_scraper"),
            ("Redis connectivity", "docker-compose exec redis redis-cli ping"),
        ]

        all_healthy = True
        for check_name, check_target in health_checks:
            if check_target.startswith('http'):
                # HTTP health check
                try:
                    response = requests.get(check_target, timeout=10)
                    if response.status_code == 200:
                        self.log(f"✓ {check_name} - Healthy")
                    else:
                        self.log(f"✗ {check_name} - Unhealthy (Status: {response.status_code})", 'ERROR')
                        all_healthy = False
                except Exception as e:
                    self.log(f"✗ {check_name} - Unreachable: {e}", 'ERROR')
                    all_healthy = False
            else:
                # Command-based health check
                if self.run_command(check_target, check=False):
                    self.log(f"✓ {check_name} - Healthy")
                else:
                    self.log(f"✗ {check_name} - Unhealthy", 'ERROR')
                    all_healthy = False

        return all_healthy

    def run_smoke_tests(self):
        """Run smoke tests to verify functionality"""
        self.log("Running smoke tests...")

        smoke_tests = [
            ("Create test keyword",
             "docker-compose exec web python -c \"from app.models import Keyword, db; k = Keyword(keyword='test smoke'); db.session.add(k); db.session.commit()\""),
            ("Verify keyword creation",
             "docker-compose exec web python -c \"from app.models import Keyword; print(f'Keywords in DB: {Keyword.query.count()}')\""),
            ("Test Celery worker", "docker-compose exec celery-worker celery -A app.tasks.celery inspect active"),
        ]

        all_passed = True
        for test_name, test_command in smoke_tests:
            if self.run_command(test_command, check=False):
                self.log(f"✓ {test_name} - Passed")
            else:
                self.log(f"✗ {test_name} - Failed", 'ERROR')
                all_passed = False

        return all_passed

    def generate_deployment_report(self):
        """Generate deployment report"""
        deployment_time = datetime.now() - self.start_time

        report = {
            'deployment_id': self.start_time.strftime('%Y%m%d_%H%M%S'),
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration_seconds': deployment_time.total_seconds(),
            'log_entries': self.deployment_log,
            'summary': {
                'total_steps': len(self.deployment_log),
                'successful': all('ERROR' not in entry for entry in self.deployment_log),
                'warnings': len([entry for entry in self.deployment_log if 'WARNING' in entry])
            }
        }

        # Save report to file
        report_filename = f"deployment_report_{report['deployment_id']}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)

        self.log(f"Deployment report saved to: {report_filename}")
        return report

    def deploy(self):
        """Execute complete deployment process"""
        self.log("Starting final deployment process...")

        try:
            # Phase 1: Pre-deployment checks
            if not self.check_prerequisites():
                self.log("Prerequisites check failed", 'ERROR')
                return False

            self.load_environment()

            if not self.run_security_scan():
                self.log("Security scan found issues", 'WARNING')
                # Continue despite warnings, but log them

            # Phase 2: Deployment
            if not self.build_and_deploy():
                return False

            # Phase 3: Post-deployment verification
            if not self.run_health_checks():
                self.log("Health checks failed", 'ERROR')
                return False

            if not self.run_smoke_tests():
                self.log("Smoke tests failed", 'ERROR')
                return False

            # Phase 4: Finalization
            report = self.generate_deployment_report()

            if report['summary']['successful']:
                self.log("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
                self.log(f"📊 Deployment took {report['duration_seconds']:.2f} seconds")
                self.log("🔗 Application is available at: http://localhost:5000")
                self.log("📚 API Documentation: http://localhost:5000/api/docs")
                self.log("📈 Monitoring Dashboard: http://localhost:5000/admin/monitoring")
                return True
            else:
                self.log("💥 DEPLOYMENT FAILED", 'ERROR')
                return False

        except Exception as e:
            self.log(f"Deployment process failed with exception: {e}", 'ERROR')
            return False


if __name__ == "__main__":
    deployment = FinalDeployment()

    if deployment.deploy():
        sys.exit(0)
    else:
        sys.exit(1)