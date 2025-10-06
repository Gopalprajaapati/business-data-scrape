# config.py
import os
import json
from datetime import timedelta
from typing import Dict, Any


class Config:
    """Base configuration"""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///business_scraper.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_timeout': 30,
        'max_overflow': 20,
        'pool_size': 10
    }

    # File Upload
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

    # Scraping Configuration
    SCRAPING_CONFIG = {
        'max_concurrent_scrapers': int(os.environ.get('MAX_CONCURRENT_SCRAPERS', 3)),
        'request_timeout': int(os.environ.get('REQUEST_TIMEOUT', 30)),
        'max_results_per_keyword': int(os.environ.get('MAX_RESULTS', 100)),
        'retry_attempts': int(os.environ.get('RETRY_ATTEMPTS', 3)),
        'delay_between_requests': float(os.environ.get('REQUEST_DELAY', 2.0)),
        'use_proxies': os.environ.get('USE_PROXIES', 'False').lower() == 'true',
        'headless_browser': os.environ.get('HEADLESS_BROWSER', 'True').lower() == 'true'
    }

    # Analysis Configuration
    ANALYSIS_CONFIG = {
        'cache_duration_hours': int(os.environ.get('ANALYSIS_CACHE_HOURS', 24)),
        'timeout_seconds': int(os.environ.get('ANALYSIS_TIMEOUT', 30)),
        'max_content_size_mb': int(os.environ.get('MAX_CONTENT_SIZE', 5)),
        'enable_advanced_analysis': os.environ.get('ADVANCED_ANALYSIS', 'True').lower() == 'true'
    }

    # Celery Configuration
    CELERY_CONFIG = {
        'broker_url': os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        'result_backend': os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        'task_serializer': 'json',
        'result_serializer': 'json',
        'accept_content': ['json'],
        'timezone': 'UTC',
        'enable_utc': True,
        'task_routes': {
            'app.tasks.scrape_keyword': {'queue': 'scraping'},
            'app.tasks.analyze_website': {'queue': 'analysis'},
            'app.tasks.generate_report': {'queue': 'reporting'}
        }
    }

    # Email Configuration
    EMAIL_CONFIG = {
        'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
        'sender_email': os.environ.get('SENDER_EMAIL', ''),
        'sender_password': os.environ.get('SENDER_PASSWORD', ''),
        'admin_email': os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    }

    # Security Configuration
    SECURITY_CONFIG = {
        'rate_limiting': {
            'enabled': os.environ.get('RATE_LIMITING', 'True').lower() == 'true',
            'requests_per_minute': int(os.environ.get('RATE_LIMIT_PER_MINUTE', 100)),
            'storage_uri': os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        },
        'cors': {
            'enabled': os.environ.get('CORS_ENABLED', 'True').lower() == 'true',
            'origins': json.loads(os.environ.get('CORS_ORIGINS', '["http://localhost:3000"]'))
        }
    }

    # Monitoring Configuration
    MONITORING_CONFIG = {
        'enable_health_checks': os.environ.get('HEALTH_CHECKS', 'True').lower() == 'true',
        'enable_metrics': os.environ.get('ENABLE_METRICS', 'True').lower() == 'true',
        'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
        'enable_audit_log': os.environ.get('AUDIT_LOG', 'True').lower() == 'true'
    }

    # Performance Configuration
    PERFORMANCE_CONFIG = {
        'enable_caching': os.environ.get('ENABLE_CACHING', 'True').lower() == 'true',
        'cache_timeout': int(os.environ.get('CACHE_TIMEOUT', 300)),
        'database_pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'background_worker_count': int(os.environ.get('WORKER_COUNT', 4))
    }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    # Development-specific settings
    SCRAPING_CONFIG = {
        **Config.SCRAPING_CONFIG,
        'max_concurrent_scrapers': 2,
        'headless_browser': True
    }

    # Enable detailed logging
    MONITORING_CONFIG = {
        **Config.MONITORING_CONFIG,
        'log_level': 'DEBUG'
    }


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

    # Use in-memory database for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Disable external services in tests
    SCRAPING_CONFIG = {
        **Config.SCRAPING_CONFIG,
        'use_proxies': False,
        'headless_browser': True
    }

    # Mock email sending
    EMAIL_CONFIG = {
        **Config.EMAIL_CONFIG,
        'sender_email': 'test@example.com'
    }


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    # Production security
    SECRET_KEY = os.environ.get('SECRET_KEY')

    if not SECRET_KEY:
        raise ValueError("SECRET_KEY must be set in production")

    # Production performance
    SCRAPING_CONFIG = {
        **Config.SCRAPING_CONFIG,
        'max_concurrent_scrapers': int(os.environ.get('MAX_CONCURRENT_SCRAPERS', 5)),
        'use_proxies': True
    }

    # Production monitoring
    MONITORING_CONFIG = {
        **Config.MONITORING_CONFIG,
        'log_level': 'INFO',
        'enable_metrics': True
    }

    # Production database
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'pool_size': 20,
        'max_overflow': 30
    }


# Configuration factory
def get_config(config_name=None):
    """Get configuration based on environment"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    config_mapping = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
        'default': DevelopmentConfig
    }

    return config_mapping.get(config_name, DevelopmentConfig)


# Configuration manager
class ConfigManager:
    def __init__(self):
        self.config = get_config()
        self._dynamic_settings = {}

    def get(self, key, default=None):
        """Get configuration value"""
        try:
            # Check dynamic settings first
            if key in self._dynamic_settings:
                return self._dynamic_settings[key]

            # Check nested configurations
            keys = key.split('.')
            value = self.config

            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, {})
                else:
                    value = getattr(value, k, {})

            return value if value != {} else default

        except (AttributeError, KeyError):
            return default

    def set(self, key, value):
        """Set dynamic configuration value"""
        self._dynamic_settings[key] = value

    def update_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary"""
        for key, value in config_dict.items():
            self.set(key, value)

    def get_scraping_config(self):
        """Get scraping configuration"""
        return self.get('SCRAPING_CONFIG', {})

    def get_database_config(self):
        """Get database configuration"""
        return {
            'database_uri': self.get('SQLALCHEMY_DATABASE_URI'),
            'engine_options': self.get('SQLALCHEMY_ENGINE_OPTIONS', {})
        }

    def validate_config(self):
        """Validate configuration settings"""
        errors = []

        # Validate required settings
        if not self.get('SECRET_KEY') or self.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
            errors.append("SECRET_KEY must be set and secure in production")

        # Validate email configuration if enabled
        if self.get('EMAIL_CONFIG.sender_email'):
            if not self.get('EMAIL_CONFIG.sender_password'):
                errors.append("Email password required if sender email is set")

        # Validate scraping configuration
        scraping_config = self.get_scraping_config()
        if scraping_config.get('max_concurrent_scrapers', 0) > 10:
            errors.append("Too many concurrent scrapers configured")

        return errors