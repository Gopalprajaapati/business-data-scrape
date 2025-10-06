# app/configuration/__init__.py
import json
import yaml
from datetime import datetime
import logging
from flask import current_app
from app.security import SecurityManager

logger = logging.getLogger(__name__)


class ConfigurationManager:
    def __init__(self, app=None):
        self.app = app
        self.config_version = '1.0'
        self.config_history = []

    def init_app(self, app):
        """Initialize configuration manager with Flask app"""
        self.app = app
        self.load_configuration()

    def load_configuration(self):
        """Load configuration from database or file"""
        try:
            # Try to load from database first
            config_data = self.load_from_database()
            if config_data:
                self.apply_configuration(config_data)
                logger.info("Configuration loaded from database")
            else:
                # Fall back to file-based configuration
                self.load_from_file()
                logger.info("Configuration loaded from file")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def load_from_database(self):
        """Load configuration from database"""
        # This would query a configuration table in the database
        # For now, return None to use file-based config
        return None

    def load_from_file(self, config_file='config/settings.yaml'):
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                self.apply_configuration(config_data)

        except FileNotFoundError:
            logger.warning(f"Configuration file {config_file} not found, using defaults")
            self.apply_default_configuration()
        except Exception as e:
            logger.error(f"Failed to load configuration from file: {e}")
            self.apply_default_configuration()

    def apply_configuration(self, config_data):
        """Apply configuration to Flask app"""
        try:
            # Scraping configuration
            scraping_config = config_data.get('scraping', {})
            current_app.config['SCRAPING_CONFIG'].update(scraping_config)

            # Analysis configuration
            analysis_config = config_data.get('analysis', {})
            current_app.config['ANALYSIS_CONFIG'].update(analysis_config)

            # Security configuration
            security_config = config_data.get('security', {})
            current_app.config['SECURITY_CONFIG'].update(security_config)

            # Monitoring configuration
            monitoring_config = config_data.get('monitoring', {})
            current_app.config['MONITORING_CONFIG'].update(monitoring_config)

            # Performance configuration
            performance_config = config_data.get('performance', {})
            current_app.config['PERFORMANCE_CONFIG'].update(performance_config)

            logger.info("Configuration applied successfully")

        except Exception as e:
            logger.error(f"Failed to apply configuration: {e}")
            raise

    def apply_default_configuration(self):
        """Apply default configuration"""
        default_config = {
            'scraping': {
                'max_concurrent_scrapers': 3,
                'request_timeout': 30,
                'max_results_per_keyword': 100,
                'retry_attempts': 3
            },
            'analysis': {
                'cache_duration_hours': 24,
                'timeout_seconds': 30,
                'enable_advanced_analysis': True
            },
            'security': {
                'rate_limiting': {
                    'enabled': True,
                    'requests_per_minute': 100
                }
            }
        }

        self.apply_configuration(default_config)

    def update_configuration(self, new_config, user_id='system'):
        """Update system configuration"""
        try:
            # Validate configuration
            self.validate_configuration(new_config)

            # Create backup of current configuration
            backup_config = self.get_current_configuration()
            self.config_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'config': backup_config,
                'version': self.config_version
            })

            # Keep only last 10 configurations
            if len(self.config_history) > 10:
                self.config_history = self.config_history[-10:]

            # Apply new configuration
            self.apply_configuration(new_config)

            # Save to database if available
            self.save_to_database(new_config)

            # Log the configuration change
            logger.info(f"Configuration updated by user {user_id}")

            return {
                'success': True,
                'message': 'Configuration updated successfully',
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Configuration update failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def validate_configuration(self, config_data):
        """Validate configuration data"""
        # Validate scraping configuration
        scraping_config = config_data.get('scraping', {})
        if 'max_concurrent_scrapers' in scraping_config:
            max_scrapers = scraping_config['max_concurrent_scrapers']
            if not isinstance(max_scrapers, int) or max_scrapers < 1 or max_scrapers > 10:
                raise ValueError("max_concurrent_scrapers must be between 1 and 10")

        # Validate security configuration
        security_config = config_data.get('security', {})
        rate_limiting = security_config.get('rate_limiting', {})
        if 'requests_per_minute' in rate_limiting:
            rpm = rate_limiting['requests_per_minute']
            if not isinstance(rpm, int) or rpm < 10 or rpm > 1000:
                raise ValueError("requests_per_minute must be between 10 and 1000")

    def get_current_configuration(self):
        """Get current system configuration"""
        return {
            'scraping': current_app.config['SCRAPING_CONFIG'],
            'analysis': current_app.config['ANALYSIS_CONFIG'],
            'security': current_app.config['SECURITY_CONFIG'],
            'monitoring': current_app.config['MONITORING_CONFIG'],
            'performance': current_app.config['PERFORMANCE_CONFIG']
        }

    def save_to_database(self, config_data):
        """Save configuration to database"""
        # This would save to a configuration table in the database
        # For now, just log the action
        logger.info("Configuration saved to database")

    def export_configuration(self, format='json'):
        """Export current configuration"""
        config_data = self.get_current_configuration()

        if format == 'json':
            return json.dumps(config_data, indent=2)
        elif format == 'yaml':
            return yaml.dump(config_data, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_configuration_history(self):
        """Get configuration change history"""
        return self.config_history

    def rollback_configuration(self, version_index=-1):
        """Rollback to previous configuration version"""
        try:
            if not self.config_history:
                raise ValueError("No configuration history available")

            if version_index >= len(self.config_history) or version_index < -len(self.config_history):
                raise ValueError("Invalid version index")

            # Get the target configuration
            target_config = self.config_history[version_index]['config']

            # Apply the configuration
            self.apply_configuration(target_config)

            logger.info(f"Configuration rolled back to version {version_index}")

            return {
                'success': True,
                'message': f'Configuration rolled back to version {version_index}',
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Configuration rollback failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global configuration manager instance
config_manager = ConfigurationManager()