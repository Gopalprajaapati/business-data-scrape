# app/tasks/__init__.py
from celery import Celery, current_task
from celery.signals import task_prerun, task_postrun, task_failure
import time
import logging
from app import create_app
from app.monitoring import AdvancedLogger


def make_celery(app):
    """Create Celery application"""
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_CONFIG']['result_backend'],
        broker=app.config['CELERY_CONFIG']['broker_url']
    )

    celery.conf.update(app.config['CELERY_CONFIG'])

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# Create Celery app
flask_app = create_app()
celery = make_celery(flask_app)

# Task monitoring
logger = AdvancedLogger('celery')


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extras):
    """Handle task pre-run events"""
    logger.logger.info(f"Task started: {task.name} [{task_id}]")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None,
                         **extras):
    """Handle task post-run events"""
    logger.logger.info(f"Task completed: {task.name} [{task_id}] - State: {state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **extras):
    """Handle task failure events"""
    logger.logger.error(f"Task failed: {sender.name} [{task_id}] - {exception}")


# Task routes for different queues
celery.conf.task_routes = {
    'app.tasks.scraping.*': {'queue': 'scraping'},
    'app.tasks.analysis.*': {'queue': 'analysis'},
    'app.tasks.reporting.*': {'queue': 'reporting'},
    'app.tasks.maintenance.*': {'queue': 'maintenance'},
}