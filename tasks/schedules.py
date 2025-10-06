# app/tasks/schedules.py
from celery.schedules import crontab
from datetime import timedelta

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    # Database maintenance - daily at 2 AM
    'database-maintenance-daily': {
        'task': 'app.tasks.maintenance.database_maintenance_task',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'maintenance'}
    },

    # Cache cleanup - every 6 hours
    'cache-cleanup-6hours': {
        'task': 'app.tasks.maintenance.cache_cleanup_task',
        'schedule': timedelta(hours=6),
        'options': {'queue': 'maintenance'}
    },

    # System health check - every 30 minutes
    'system-health-check-30min': {
        'task': 'app.tasks.maintenance.system_health_check_task',
        'schedule': timedelta(minutes=30),
        'options': {'queue': 'maintenance'}
    },

    # Daily summary report - daily at 8 AM
    'daily-summary-report': {
        'task': 'app.tasks.reporting.generate_daily_summary_report',
        'schedule': crontab(hour=8, minute=0),
        'options': {'queue': 'reporting'}
    },

    # Memory optimization - every hour
    'memory-optimization-hourly': {
        'task': 'app.tasks.maintenance.memory_optimization_task',
        'schedule': timedelta(hours=1),
        'options': {'queue': 'maintenance'}
    },
}


# Update Celery configuration
def update_celery_schedule(celery_app):
    celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
    celery_app.conf.timezone = 'UTC'