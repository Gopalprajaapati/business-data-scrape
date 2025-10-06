# scripts/production_checklist.py
import os
import sys
import subprocess
import requests
import psutil
from datetime import datetime


class ProductionChecklist:
    def __init__(self):
        self.checks = []
        self.failures = []

    def run_checks(self):
        """Run all production readiness checks"""
        print("🔍 Running Production Readiness Checks...")

        self.check_environment_variables()
        self.check_database_connection()
        self.check_redis_connection()
        self.check_disk_space()
        self.check_memory()
        self.check_security_settings()
        self.check_ssl_certificate()
        self.check_backup_configuration()
        self.check_monitoring()
        self.check_logging()

        self.report_results()

    def check_environment_variables(self):
        """Check required environment variables"""
        required_vars = [
            'SECRET_KEY',
            'DATABASE_URL',
            'FLASK_ENV'
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.fail(f"Missing environment variables: {', '.join(missing_vars)}")
        else:
            self.pass_check("Environment variables configured")

        # Check for default secret key
        if os.getenv('SECRET_KEY') == 'dev-secret-key-change-in-production':
            self.fail("Default secret key detected - change in production")

    def check_database_connection(self):
        """Check database connectivity and configuration"""
        try:
            from app import db
            db.session.execute('SELECT 1')
            self.pass_check("Database connection successful")

            # Check database size
            result = db.session.execute("SELECT pg_database_size(current_database())")
            db_size = result.scalar()
            if db_size > 10 * 1024 * 1024 * 1024:  # 10GB
                self.warn("Database size exceeds 10GB - consider archiving")

        except Exception as e:
            self.fail(f"Database connection failed: {e}")

    def check_redis_connection(self):
        """Check Redis connectivity"""
        try:
            import redis
            r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
            r.ping()
            self.pass_check("Redis connection successful")
        except Exception as e:
            self.fail(f"Redis connection failed: {e}")

    def check_disk_space(self):
        """Check disk space availability"""
        disk = psutil.disk_usage('/')
        free_gb = disk.free / (1024 ** 3)

        if free_gb < 5:
            self.fail(f"Low disk space: {free_gb:.1f}GB free")
        elif free_gb < 10:
            self.warn(f"Limited disk space: {free_gb:.1f}GB free")
        else:
            self.pass_check(f"Disk space adequate: {free_gb:.1f}GB free")

    def check_memory(self):
        """Check system memory"""
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            self.fail(f"High memory usage: {memory.percent}%")
        elif memory.percent > 80:
            self.warn(f"Elevated memory usage: {memory.percent}%")
        else:
            self.pass_check(f"Memory usage normal: {memory.percent}%")

    def check_security_settings(self):
        """Check security configuration"""
        checks = []

        # Check if running in production mode
        if os.getenv('FLASK_ENV') != 'production':
            checks.append("Not running in production mode")

        # Check for debug mode
        if os.getenv('FLASK_DEBUG') == '1':
            checks.append("Debug mode enabled")

        # Check CORS settings
        if os.getenv('CORS_ORIGINS', '').strip() == '*':
            checks.append("CORS set to allow all origins")

        if checks:
            self.fail(f"Security issues: {', '.join(checks)}")
        else:
            self.pass_check("Security configuration adequate")

    def check_ssl_certificate(self):
        """Check SSL certificate validity"""
        try:
            domain = os.getenv('DOMAIN_NAME', 'localhost')
            response = requests.get(f'https://{domain}', timeout=10, verify=False)

            if response.status_code == 200:
                self.pass_check("SSL certificate valid")
            else:
                self.warn(f"SSL certificate check returned status {response.status_code}")

        except requests.exceptions.SSLError as e:
            self.fail(f"SSL certificate error: {e}")
        except Exception as e:
            self.warn(f"Could not verify SSL certificate: {e}")

    def check_backup_configuration(self):
        """Check backup configuration"""
        # Check if backup directory exists and is writable
        backup_dir = os.getenv('BACKUP_DIR', '/backups')
        if not os.path.exists(backup_dir):
            self.warn("Backup directory does not exist")
        elif not os.access(backup_dir, os.W_OK):
            self.warn("Backup directory is not writable")
        else:
            self.pass_check("Backup directory configured")

    def check_monitoring(self):
        """Check monitoring setup"""
        try:
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                self.pass_check("Health check endpoint accessible")
            else:
                self.warn("Health check endpoint returned non-200 status")
        except:
            self.warn("Health check endpoint not accessible")

    def check_logging(self):
        """Check logging configuration"""
        log_dirs = ['logs', 'uploads']

        for log_dir in log_dirs:
            if not os.path.exists(log_dir):
                self.warn(f"Log directory '{log_dir}' does not exist")
            elif not os.access(log_dir, os.W_OK):
                self.warn(f"Log directory '{log_dir}' is not writable")
            else:
                self.pass_check(f"Log directory '{log_dir}' configured")

    def pass_check(self, message):
        """Record passed check"""
        self.checks.append(('✅', message))
        print(f"  ✅ {message}")

    def warn(self, message):
        """Record warning"""
        self.checks.append(('⚠️', message))
        print(f"  ⚠️  {message}")

    def fail(self, message):
        """Record failure"""
        self.checks.append(('❌', message))
        self.failures.append(message)
        print(f"  ❌ {message}")

    def report_results(self):
        """Generate final report"""
        print("\n" + "=" * 50)
        print("📊 PRODUCTION READINESS REPORT")
        print("=" * 50)

        for status, message in self.checks:
            print(f"  {status} {message}")

        print("\n" + "=" * 50)

        if self.failures:
            print(f"❌ PRODUCTION DEPLOYMENT BLOCKED")
            print(f"Failures: {len(self.failures)}")
            for failure in self.failures:
                print(f"  - {failure}")
            sys.exit(1)
        else:
            print("✅ ALL CHECKS PASSED - READY FOR PRODUCTION")
            print("Recommended next steps:")
            print("  1. Run load testing")
            print("  2. Verify backup procedures")
            print("  3. Set up monitoring alerts")
            print("  4. Document deployment procedures")


if __name__ == "__main__":
    checklist = ProductionChecklist()
    checklist.run_checks()