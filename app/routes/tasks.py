# app/routes/tasks.py
from flask import Blueprint, jsonify, request
from app.tasks import celery
from celery.result import AsyncResult

bp = Blueprint('tasks', __name__, url_prefix='/api/v1/tasks')


@bp.route('/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of a specific task"""
    try:
        task_result = AsyncResult(task_id, app=celery)

        response = {
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None
        }

        if task_result.failed():
            response['error'] = str(task_result.result)

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """Cancel a running task"""
    try:
        task_result = AsyncResult(task_id, app=celery)
        task_result.revoke(terminate=True)

        return jsonify({
            'task_id': task_id,
            'status': 'cancelled'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/queue/stats', methods=['GET'])
def get_queue_stats():
    """Get queue statistics"""
    try:
        inspector = celery.control.inspect()

        # Get active tasks
        active_tasks = inspector.active() or {}

        # Get scheduled tasks
        scheduled_tasks = inspector.scheduled() or {}

        # Get reserved tasks
        reserved_tasks = inspector.reserved() or {}

        stats = {
            'queues': {
                'scraping': {
                    'active': len(active_tasks.get('scraping', [])),
                    'scheduled': len(scheduled_tasks.get('scraping', [])),
                    'reserved': len(reserved_tasks.get('scraping', []))
                },
                'analysis': {
                    'active': len(active_tasks.get('analysis', [])),
                    'scheduled': len(scheduled_tasks.get('analysis', [])),
                    'reserved': len(reserved_tasks.get('analysis', []))
                },
                'reporting': {
                    'active': len(active_tasks.get('reporting', [])),
                    'scheduled': len(scheduled_tasks.get('reporting', [])),
                    'reserved': len(reserved_tasks.get('reporting', []))
                },
                'maintenance': {
                    'active': len(active_tasks.get('maintenance', [])),
                    'scheduled': len(scheduled_tasks.get('maintenance', [])),
                    'reserved': len(reserved_tasks.get('maintenance', []))
                }
            },
            'total_active': sum(len(tasks) for tasks in active_tasks.values()),
            'total_scheduled': sum(len(tasks) for tasks in scheduled_tasks.values()),
            'total_reserved': sum(len(tasks) for tasks in reserved_tasks.values())
        }

        return jsonify(stats)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/queue/purge', methods=['POST'])
def purge_queue():
    """Purge all tasks from specified queue"""
    try:
        queue_name = request.json.get('queue_name')

        if not queue_name:
            return jsonify({'error': 'queue_name is required'}), 400

        # Purge the queue
        purged_count = celery.control.purge(queue=queue_name)

        return jsonify({
            'queue': queue_name,
            'purged_count': purged_count,
            'status': 'purged'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/workers/status', methods=['GET'])
def get_workers_status():
    """Get status of all Celery workers"""
    try:
        inspector = celery.control.inspect()

        # Get worker stats
        worker_stats = inspector.stats() or {}

        # Get active workers
        active_workers = inspector.active() or {}

        # Get registered workers
        registered_workers = inspector.registered() or {}

        workers_status = {}
        for worker_name in worker_stats.keys():
            workers_status[worker_name] = {
                'status': 'online' if worker_name in active_workers else 'offline',
                'tasks_registered': len(registered_workers.get(worker_name, [])),
                'tasks_active': len(active_workers.get(worker_name, [])),
                'stats': worker_stats[worker_name]
            }

        return jsonify(workers_status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500