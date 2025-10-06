# app/monitoring/__init__.py
import logging
import time
import psutil
from functools import wraps
from flask import request, g
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import threading
from datetime import datetime, timedelta
import json

# Prometheus Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP Request Duration')
SCRAPING_SUCCESS = Counter('scraping_success_total', 'Successful Scraping Operations')
SCRAPING_FAILURE = Counter('scraping_failure_total', 'Failed Scraping Operations')
ANALYSIS_DURATION = Histogram('analysis_duration_seconds', 'Website Analysis Duration')
DATABASE_QUERY_DURATION = Histogram('database_query_duration_seconds', 'Database Query Duration')
ACTIVE_SCRAPERS = Gauge('active_scrapers', 'Currently Active Scrapers')
QUEUE_SIZE = Gauge('queue_size', 'Current Queue Size')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory Usage')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU Usage')


class AdvancedLogger:
    def __init__(self, name=__name__):
        self.logger = logging.getLogger(name)
        self.setup_logging()

    def setup_logging(self):
        """Setup comprehensive logging configuration"""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", '
            '"file": "%(filename)s", "line": %(lineno)d, "message": "%(message)s"}'
        )

        # File handlers
        file_handler = logging.handlers.RotatingFileHandler(
            'logs/app.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(detailed_formatter)

        error_handler = logging.handlers.RotatingFileHandler(
            'logs/error.log',
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setFormatter(detailed_formatter)
        error_handler.setLevel(logging.ERROR)

        json_handler = logging.handlers.RotatingFileHandler(
            'logs/structured.log',
            maxBytes=10 * 1024 * 1024,
            backupCount=3
        )
        json_handler.setFormatter(json_formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(detailed_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(json_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate logs
        self.logger.propagate = False

    def log_scraping_operation(self, keyword, success, results_count, duration, error=None):
        """Log scraping operation with structured data"""
        log_data = {
            'operation': 'scraping',
            'keyword': keyword,
            'success': success,
            'results_count': results_count,
            'duration_seconds': duration,
            'timestamp': datetime.utcnow().isoformat()
        }

        if error:
            log_data['error'] = str(error)
            self.logger.error(json.dumps(log_data))
            SCRAPING_FAILURE.inc()
        else:
            self.logger.info(json.dumps(log_data))
            SCRAPING_SUCCESS.inc()

    def log_analysis_operation(self, url, score, duration, analysis_type='comprehensive'):
        """Log website analysis operation"""
        log_data = {
            'operation': 'analysis',
            'url': url,
            'score': score,
            'analysis_type': analysis_type,
            'duration_seconds': duration,
            'timestamp': datetime.utcnow().isoformat()
        }

        self.logger.info(json.dumps(log_data))
        ANALYSIS_DURATION.observe(duration)

    def log_database_operation(self, operation, table, duration, rows_affected=0):
        """Log database operations"""
        log_data = {
            'operation': 'database',
            'operation_type': operation,
            'table': table,
            'duration_seconds': duration,
            'rows_affected': rows_affected,
            'timestamp': datetime.utcnow().isoformat()
        }

        self.logger.debug(json.dumps(log_data))
        DATABASE_QUERY_DURATION.observe(duration)

    def log_security_event(self, event_type, user_ip, details):
        """Log security-related events"""
        log_data = {
            'operation': 'security',
            'event_type': event_type,
            'user_ip': user_ip,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }

        self.logger.warning(json.dumps(log_data))


class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
        self.start_time = datetime.utcnow()
        self.thread = None
        self.running = False

    def start_monitoring(self):
        """Start background performance monitoring"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                self.collect_system_metrics()
                time.sleep(60)  # Collect every minute
            except Exception as e:
                logging.error(f"Performance monitoring error: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    def collect_system_metrics(self):
        """Collect system performance metrics"""
        # Memory usage
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.used)

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        CPU_USAGE.set(cpu_percent)

        # Disk usage
        disk = psutil.disk_usage('/')

        # Process metrics
        process = psutil.Process()
        process_memory = process.memory_info().rss
        process_cpu = process.cpu_percent()

        # Update metrics dictionary
        self.metrics.update({
            'timestamp': datetime.utcnow().isoformat(),
            'memory_used': memory.used,
            'memory_total': memory.total,
            'memory_percent': memory.percent,
            'cpu_percent': cpu_percent,
            'disk_used': disk.used,
            'disk_total': disk.total,
            'disk_percent': disk.percent,
            'process_memory': process_memory,
            'process_cpu': process_cpu,
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds()
        })

    def get_performance_report(self):
        """Generate performance report"""
        return {
            'system': self.metrics,
            'application': {
                'active_scrapers': ACTIVE_SCRAPERS._value.get(),
                'queue_size': QUEUE_SIZE._value.get(),
                'total_requests': REQUEST_COUNT._value.get()
            }
        }

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        if self.thread:
            self.thread.join()


class AuditLogger:
    def __init__(self):
        self.logger = AdvancedLogger('audit')

    def log_user_action(self, user_id, action, resource, details=None):
        """Log user actions for audit trail"""
        audit_data = {
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': request.remote_addr if request else 'system',
            'user_agent': request.headers.get('User-Agent') if request else 'system'
        }

        if details:
            audit_data['details'] = details

        self.logger.logger.info(json.dumps(audit_data))

    def log_data_access(self, user_id, data_type, record_id, operation):
        """Log data access operations"""
        self.log_user_action(
            user_id,
            f'{operation}_access',
            data_type,
            {'record_id': record_id}
        )

    def log_system_change(self, component, change_type, old_value, new_value):
        """Log system configuration changes"""
        self.log_user_action(
            'system',
            f'{change_type}_change',
            component,
            {
                'old_value': old_value,
                'new_value': new_value
            }
        )


# Decorators for monitoring
def monitor_request(func):
    """Decorator to monitor HTTP requests"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            response = func(*args, **kwargs)
            status_code = response.status_code if hasattr(response, 'status_code') else 200

            # Record metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.endpoint,
                status=status_code
            ).inc()

            REQUEST_DURATION.observe(time.time() - start_time)

            return response

        except Exception as e:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.endpoint,
                status=500
            ).inc()
            raise e

    return wrapper


def monitor_scraping(func):
    """Decorator to monitor scraping operations"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        ACTIVE_SCRAPERS.inc()
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            # Log successful operation
            if len(args) > 0 and hasattr(args[0], 'keyword'):
                logger = AdvancedLogger('scraping')
                logger.log_scraping_operation(
                    args[0].keyword,
                    True,
                    len(result) if isinstance(result, list) else 0,
                    duration
                )

            return result

        except Exception as e:
            duration = time.time() - start_time

            # Log failed operation
            if len(args) > 0 and hasattr(args[0], 'keyword'):
                logger = AdvancedLogger('scraping')
                logger.log_scraping_operation(
                    args[0].keyword,
                    False,
                    0,
                    duration,
                    error=e
                )
            raise e

        finally:
            ACTIVE_SCRAPERS.dec()

    return wrapper


def monitor_database(func):
    """Decorator to monitor database operations"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            # Log database operation
            logger = AdvancedLogger('database')
            logger.log_database_operation(
                func.__name__,
                args[0].__class__.__name__ if args else 'unknown',
                duration,
                len(result) if isinstance(result, list) else 1
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            logger = AdvancedLogger('database')
            logger.log_database_operation(
                func.__name__,
                args[0].__class__.__name__ if args else 'unknown',
                duration,
                0
            )
            raise e

    return wrapper


# Flask routes for monitoring
@app.route('/metrics')
def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return generate_latest()


@app.route('/health')
def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }

    # Database health check
    try:
        from app.models import db
        db.session.execute('SELECT 1')
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = 'unhealthy'
        health_status['status'] = 'unhealthy'

    # Redis health check
    try:
        import redis
        r = redis.from_url(app.config['CELERY_BROKER_URL'])
        r.ping()
        health_status['checks']['redis'] = 'healthy'
    except Exception as e:
        health_status['checks']['redis'] = 'unhealthy'
        health_status['status'] = 'unhealthy'

    # Disk space check
    try:
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            health_status['checks']['disk'] = 'warning'
            health_status['status'] = 'degraded'
        else:
            health_status['checks']['disk'] = 'healthy'
    except Exception as e:
        health_status['checks']['disk'] = 'unhealthy'
        health_status['status'] = 'unhealthy'

    return jsonify(health_status)


@app.route('/status')
def system_status():
    """Detailed system status endpoint"""
    monitor = PerformanceMonitor()

    status = {
        'application': {
            'version': '1.0.0',
            'environment': app.config.get('FLASK_ENV', 'development'),
            'uptime': monitor.metrics.get('uptime_seconds', 0)
        },
        'performance': monitor.get_performance_report(),
        'resources': {
            'keywords_count': Keyword.query.count(),
            'results_count': SearchResult.query.count(),
            'analyses_count': WebsiteAnalysis.query.count()
        }
    }

    return jsonify(status)