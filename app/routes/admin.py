# app/routes/admin.py
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models import db, Keyword, SearchResult, WebsiteAnalysis
from app.monitoring import PerformanceMonitor, AuditLogger
from app.tasks import celery
from app.websockets import realtime_dashboard
from datetime import datetime, timedelta
import json

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard page"""
    return render_template('admin/dashboard.html')


@bp.route('/api/system-overview')
@login_required
def system_overview():
    """Get system overview data for admin dashboard"""
    try:
        # Performance metrics
        monitor = PerformanceMonitor()
        performance_data = monitor.get_performance_report()

        # Database statistics
        db_stats = {
            'keywords_total': Keyword.query.count(),
            'keywords_pending': Keyword.query.filter_by(status='pending').count(),
            'keywords_in_progress': Keyword.query.filter_by(status='in_progress').count(),
            'keywords_completed': Keyword.query.filter_by(status='completed').count(),
            'results_total': SearchResult.query.count(),
            'analyses_total': WebsiteAnalysis.query.count(),
            'websites_analyzed': SearchResult.query.filter(SearchResult.website.isnot(None)).count()
        }

        # Recent activity
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_activity = {
            'keywords_added': Keyword.query.filter(Keyword.created_at >= last_24h).count(),
            'results_scraped': SearchResult.query.filter(SearchResult.created_at >= last_24h).count(),
            'analyses_completed': WebsiteAnalysis.query.filter(WebsiteAnalysis.created_at >= last_24h).count()
        }

        # Task queue status
        inspector = celery.control.inspect()
        queue_stats = {
            'active_tasks': len(inspector.active() or {}),
            'scheduled_tasks': len(inspector.scheduled() or {}),
            'reserved_tasks': len(inspector.reserved() or {})
        }

        # WebSocket connections
        ws_stats = {
            'active_connections': len(realtime_dashboard.active_connections),
            'active_rooms': len(realtime_dashboard.room_subscriptions)
        }

        overview = {
            'timestamp': datetime.utcnow().isoformat(),
            'performance': performance_data,
            'database': db_stats,
            'recent_activity': recent_activity,
            'task_queues': queue_stats,
            'websocket': ws_stats
        }

        return jsonify({'success': True, 'data': overview})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/user-activity')
@login_required
def user_activity():
    """Get user activity data"""
    try:
        # This would query user activity logs
        # For now, return mock data
        activity_data = {
            'recent_logins': [
                {
                    'user': 'admin',
                    'ip_address': '192.168.1.100',
                    'timestamp': (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
                    'action': 'login'
                },
                {
                    'user': 'analyst',
                    'ip_address': '192.168.1.101',
                    'timestamp': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    'action': 'login'
                }
            ],
            'api_usage': {
                'total_requests': 1250,
                'successful_requests': 1180,
                'failed_requests': 70,
                'popular_endpoints': [
                    {'endpoint': '/api/v1/scrape', 'count': 450},
                    {'endpoint': '/api/v1/analyze', 'count': 320},
                    {'endpoint': '/api/v1/search', 'count': 280}
                ]
            }
        }

        return jsonify({'success': True, 'data': activity_data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/task-management')
@login_required
def task_management():
    """Get task management data"""
    try:
        inspector = celery.control.inspect()

        # Active tasks
        active_tasks = inspector.active() or {}
        scheduled_tasks = inspector.scheduled() or {}

        task_data = {
            'active_tasks': self.format_task_data(active_tasks),
            'scheduled_tasks': self.format_task_data(scheduled_tasks),
            'queues': {
                'scraping': len(active_tasks.get('scraping', [])),
                'analysis': len(active_tasks.get('analysis', [])),
                'reporting': len(active_tasks.get('reporting', [])),
                'maintenance': len(active_tasks.get('maintenance', []))
            }
        }

        return jsonify({'success': True, 'data': task_data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/task-management/purge-queue', methods=['POST'])
@login_required
def purge_queue():
    """Purge a specific task queue"""
    try:
        data = request.get_json()
        queue_name = data.get('queue_name')

        if not queue_name:
            return jsonify({'success': False, 'error': 'Queue name is required'}), 400

        # Purge the queue
        purged_count = celery.control.purge(queue=queue_name)

        # Log the action
        audit_logger = AuditLogger()
        audit_logger.log_user_action(
            current_user.id,
            'purge_queue',
            f'queue_{queue_name}',
            {'purged_count': purged_count}
        )

        return jsonify({
            'success': True,
            'message': f'Purged {purged_count} tasks from {queue_name}',
            'purged_count': purged_count
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/system-maintenance/optimize-db', methods=['POST'])
@login_required
def optimize_database():
    """Trigger database optimization"""
    try:
        from app.optimization import DatabaseManager

        db_manager = DatabaseManager(db)
        result = db_manager.optimize_database()

        # Log the action
        audit_logger = AuditLogger()
        audit_logger.log_user_action(
            current_user.id,
            'optimize_database',
            'system',
            {'result': result}
        )

        return jsonify({
            'success': True,
            'message': 'Database optimization completed',
            'result': result
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/system-maintenance/clear-cache', methods=['POST'])
@login_required
def clear_cache():
    """Clear application cache"""
    try:
        from app.optimization import CacheManager

        cache_manager = CacheManager()
        cache_manager.clear()

        # Log the action
        audit_logger = AuditLogger()
        audit_logger.log_user_action(
            current_user.id,
            'clear_cache',
            'system',
            {'cache_cleared': True}
        )

        return jsonify({
            'success': True,
            'message': 'Application cache cleared successfully'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/audit-logs')
@login_required
def audit_logs():
    """Get audit logs"""
    try:
        # This would query the audit log database
        # For now, return mock data
        logs = [
            {
                'id': 1,
                'user_id': 'admin',
                'action': 'purge_queue',
                'resource': 'queue_scraping',
                'timestamp': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                'ip_address': '192.168.1.100',
                'details': {'purged_count': 5}
            },
            {
                'id': 2,
                'user_id': 'analyst',
                'action': 'export_data',
                'resource': 'keyword_123',
                'timestamp': (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                'ip_address': '192.168.1.101',
                'details': {'format': 'excel', 'record_count': 150}
            }
        ]

        return jsonify({'success': True, 'data': logs})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def format_task_data(self, tasks_dict):
    """Format task data for API response"""
    formatted_tasks = []

    for worker, tasks in tasks_dict.items():
        for task in tasks:
            formatted_tasks.append({
                'worker': worker,
                'task_id': task.get('id'),
                'name': task.get('name'),
                'args': task.get('args', []),
                'kwargs': task.get('kwargs', {}),
                'started': task.get('time_start'),
                'state': task.get('state', 'UNKNOWN')
            })

    return formatted_tasks