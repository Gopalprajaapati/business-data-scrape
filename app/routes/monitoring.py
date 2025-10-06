# app/routes/monitoring.py
from flask import Blueprint, jsonify, render_template
from prometheus_client import generate_latest, CollectorRegistry
import psutil
import time
from datetime import datetime, timedelta
from app.models import Keyword, SearchResult, WebsiteAnalysis, db
from app.tasks import celery

bp = Blueprint('monitoring', __name__, url_prefix='/admin/monitoring')


@bp.route('/dashboard')
def monitoring_dashboard():
    """Monitoring dashboard page"""
    return render_template('admin/monitoring_dashboard.html')


@bp.route('/api/system-stats')
def system_stats():
    """Get system statistics for dashboard"""
    # System metrics
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    cpu_percent = psutil.cpu_percent(interval=1)

    # Application metrics
    total_keywords = Keyword.query.count()
    total_results = SearchResult.query.count()
    total_analyses = WebsiteAnalysis.query.count()

    # Recent activity (last 24 hours)
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_keywords = Keyword.query.filter(Keyword.created_at >= last_24h).count()
    recent_results = SearchResult.query.filter(SearchResult.created_at >= last_24h).count()

    # Task queue status
    inspector = celery.control.inspect()
    active_tasks = inspector.active() or {}
    total_active_tasks = sum(len(tasks) for tasks in active_tasks.values())

    stats = {
        'system': {
            'cpu_usage': cpu_percent,
            'memory_usage': memory.percent,
            'disk_usage': disk.percent,
            'uptime': int(time.time() - psutil.boot_time())
        },
        'application': {
            'total_keywords': total_keywords,
            'total_results': total_results,
            'total_analyses': total_analyses,
            'recent_keywords_24h': recent_keywords,
            'recent_results_24h': recent_results
        },
        'tasks': {
            'active_tasks': total_active_tasks,
            'queues': {
                'scraping': len(active_tasks.get('scraping', [])),
                'analysis': len(active_tasks.get('analysis', [])),
                'reporting': len(active_tasks.get('reporting', [])),
                'maintenance': len(active_tasks.get('maintenance', []))
            }
        },
        'timestamp': datetime.utcnow().isoformat()
    }

    return jsonify(stats)


@bp.route('/api/performance-metrics')
def performance_metrics():
    """Get performance metrics for charts"""
    # Get metrics for the last 7 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    # Daily keyword counts
    daily_keywords = db.session.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM keywords 
        WHERE created_at BETWEEN :start_date AND :end_date
        GROUP BY DATE(created_at)
        ORDER BY date
    """, {'start_date': start_date, 'end_date': end_date}).fetchall()

    # Daily result counts
    daily_results = db.session.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM search_results 
        WHERE created_at BETWEEN :start_date AND :end_date
        GROUP BY DATE(created_at)
        ORDER BY date
    """, {'start_date': start_date, 'end_date': end_date}).fetchall()

    # Website quality distribution
    quality_distribution = db.session.execute("""
        SELECT 
            CASE 
                WHEN score >= 80 THEN 'Excellent (80-100)'
                WHEN score >= 60 THEN 'Good (60-79)'
                WHEN score >= 40 THEN 'Average (40-59)'
                ELSE 'Poor (0-39)'
            END as quality_band,
            COUNT(*) as count
        FROM website_analyses
        WHERE score IS NOT NULL
        GROUP BY quality_band
        ORDER BY quality_band
    """).fetchall()

    metrics = {
        'daily_keywords': [{'date': str(row[0]), 'count': row[1]} for row in daily_keywords],
        'daily_results': [{'date': str(row[0]), 'count': row[1]} for row in daily_results],
        'quality_distribution': [{'band': row[0], 'count': row[1]} for row in quality_distribution],
        'time_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }

    return jsonify(metrics)


@bp.route('/api/task-metrics')
def task_metrics():
    """Get task execution metrics"""
    # This would typically query a task metrics database
    # For now, return mock data structure

    metrics = {
        'scraping_tasks': {
            'successful': 150,
            'failed': 5,
            'average_duration': 45.2,
            'success_rate': 96.8
        },
        'analysis_tasks': {
            'successful': 320,
            'failed': 8,
            'average_duration': 12.5,
            'success_rate': 97.6
        },
        'reporting_tasks': {
            'successful': 25,
            'failed': 1,
            'average_duration': 8.3,
            'success_rate': 96.2
        }
    }

    return jsonify(metrics)