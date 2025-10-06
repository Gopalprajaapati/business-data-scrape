# app/tasks/maintenance.py
from app.tasks import celery, logger
from app.optimization import DatabaseManager, MemoryOptimizer
from app.models import db
from datetime import datetime, timedelta
import psutil


@celery.task
def database_maintenance_task():
    """Scheduled task for database maintenance"""
    try:
        logger.logger.info("Starting database maintenance")

        db_manager = DatabaseManager(db)

        # Optimize database
        db_manager.optimize_database()

        # Clean up old data (keep only 90 days of data)
        db_manager.cleanup_old_data(days_old=90)

        # Update statistics
        db_manager.update_table_statistics()

        logger.logger.info("Database maintenance completed")

        return {
            'operation': 'database_maintenance',
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.logger.error(f"Database maintenance failed: {str(e)}")
        return {
            'operation': 'database_maintenance',
            'error': str(e),
            'status': 'failed'
        }


@celery.task
def cache_cleanup_task():
    """Scheduled task for cache cleanup"""
    try:
        logger.logger.info("Starting cache cleanup")

        from app.optimization import CacheManager
        cache_manager = CacheManager()

        # Clear expired cache entries
        # This would be implemented in the CacheManager class
        cache_manager.clear_expired()

        logger.logger.info("Cache cleanup completed")

        return {
            'operation': 'cache_cleanup',
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.logger.error(f"Cache cleanup failed: {str(e)}")
        return {
            'operation': 'cache_cleanup',
            'error': str(e),
            'status': 'failed'
        }


@celery.task
def system_health_check_task():
    """Scheduled task for system health checks"""
    try:
        logger.logger.info("Running system health check")

        health_checks = {}

        # Check disk space
        disk = psutil.disk_usage('/')
        health_checks['disk_usage'] = disk.percent
        health_checks['disk_alert'] = disk.percent > 90

        # Check memory
        memory = psutil.virtual_memory()
        health_checks['memory_usage'] = memory.percent
        health_checks['memory_alert'] = memory.percent > 85

        # Check database connections
        from app.optimization import DatabaseConnectionPool
        db_pool = DatabaseConnectionPool(db)
        conn_stats = db_pool.get_connection_stats()
        health_checks['database_connections'] = conn_stats
        health_checks['database_alert'] = conn_stats.get('connection_utilization', 0) > 80

        # Send alerts for critical issues
        if health_checks['disk_alert'] or health_checks['memory_alert'] or health_checks['database_alert']:
            from app.services.notifier import NotificationService
            notifier = NotificationService()

            alert_message = "System health check detected issues:\n"
            if health_checks['disk_alert']:
                alert_message += f"- Disk usage: {health_checks['disk_usage']}%\n"
            if health_checks['memory_alert']:
                alert_message += f"- Memory usage: {health_checks['memory_usage']}%\n"
            if health_checks['database_alert']:
                alert_message += f"- Database connection utilization: {health_checks['database_connections']['connection_utilization']}%\n"

            notifier.send_system_alert('health_check_warning', alert_message, 'warning')

        logger.logger.info("System health check completed")

        return {
            'operation': 'system_health_check',
            'health_checks': health_checks,
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.logger.error(f"System health check failed: {str(e)}")
        return {
            'operation': 'system_health_check',
            'error': str(e),
            'status': 'failed'
        }