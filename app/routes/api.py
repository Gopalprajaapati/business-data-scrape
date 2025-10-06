# app/routes/api.py
from flask import Blueprint, jsonify, request
from app.services.scraper import AdvancedScraperService
from app.services.analyzer import IntelligentWebsiteAnalyzer
from app.services.reporter import BusinessIntelligenceReporter
from app.services.scheduler import IntelligentScheduler
from app import db

bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Initialize services
scraper_service = AdvancedScraperService()
analyzer_service = IntelligentWebsiteAnalyzer()
reporter_service = BusinessIntelligenceReporter()
scheduler_service = IntelligentScheduler()


@bp.route('/scrape', methods=['POST'])
def api_scrape_keyword():
    """API endpoint for immediate scraping"""
    data = request.get_json()

    if not data or 'keyword' not in data:
        return jsonify({'error': 'Keyword required'}), 400

    keyword = data['keyword']
    max_results = data.get('max_results', 50)

    try:
        results = scraper_service.scrape_google_maps_advanced(keyword, max_results)

        return jsonify({
            'success': True,
            'keyword': keyword,
            'results_count': len(results),
            'results': results[:10]  # Return first 10 results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/analyze/website', methods=['POST'])
def api_analyze_website():
    """API endpoint for website analysis"""
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({'error': 'URL required'}), 400

    url = data['url']
    analysis_type = data.get('analysis_type', 'comprehensive')

    try:
        if analysis_type == 'comprehensive':
            analysis = analyzer_service.comprehensive_analysis(url)
        else:
            analysis = analyzer_service.basic_website_analysis(url)

        return jsonify({
            'success': True,
            'url': url,
            'analysis': analysis
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/reports/generate', methods=['POST'])
def api_generate_report():
    """API endpoint for report generation"""
    data = request.get_json()

    if not data or 'keyword_id' not in data:
        return jsonify({'error': 'Keyword ID required'}), 400

    keyword_id = data['keyword_id']
    report_type = data.get('report_type', 'executive')
    format_type = data.get('format', 'json')

    try:
        report = reporter_service.generate_comprehensive_report(keyword_id, report_type)

        if format_type == 'pdf' and report:
            return jsonify({
                'success': True,
                'report_url': f'/api/v1/reports/download/{keyword_id}.pdf'
            })
        elif format_type == 'excel' and report:
            return jsonify({
                'success': True,
                'report_url': f'/api/v1/reports/download/{keyword_id}.xlsx'
            })
        else:
            return jsonify({
                'success': True,
                'report': report
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/schedule/scraping', methods=['POST'])
def api_schedule_scraping():
    """API endpoint for scheduling scraping tasks"""
    data = request.get_json()

    if not data or 'keyword_id' not in data:
        return jsonify({'error': 'Keyword ID required'}), 400

    keyword_id = data['keyword_id']
    priority = data.get('priority', 'medium')

    try:
        success = scheduler_service.schedule_optimal_scraping(keyword_id, priority)

        return jsonify({
            'success': success,
            'message': f"Scraping scheduled for keyword {keyword_id}",
            'scheduled_tasks': scheduler_service.get_scheduled_tasks().get(keyword_id, [])
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/analytics/dashboard', methods=['GET'])
def api_dashboard_analytics():
    """API endpoint for dashboard analytics"""
    try:
        # Comprehensive analytics data
        analytics_data = {
            'summary': get_system_summary(),
            'performance': get_performance_metrics(),
            'recent_activity': get_recent_activity(),
            'upcoming_tasks': get_upcoming_tasks()
        }

        return jsonify({
            'success': True,
            'analytics': analytics_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/batch/operations', methods=['POST'])
def api_batch_operations():
    """API endpoint for batch operations"""
    data = request.get_json()

    if not data or 'operation' not in data:
        return jsonify({'error': 'Operation type required'}), 400

    operation = data['operation']
    keyword_ids = data.get('keyword_ids', [])

    try:
        if operation == 'scrape':
            # Schedule batch scraping
            scheduler_service.schedule_batch_processing(keyword_ids)
            message = f"Scheduled batch scraping for {len(keyword_ids)} keywords"

        elif operation == 'analyze':
            # Batch website analysis
            analyzed_count = batch_analyze_websites(keyword_ids)
            message = f"Analyzed {analyzed_count} websites"

        elif operation == 'report':
            # Generate batch reports
            reports_generated = generate_batch_reports(keyword_ids)
            message = f"Generated {reports_generated} reports"

        else:
            return jsonify({'error': 'Invalid operation'}), 400

        return jsonify({
            'success': True,
            'message': message,
            'operation': operation
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Helper functions for API endpoints
def get_system_summary():
    """Get system summary statistics"""
    from app.models import Keyword, SearchResult, WebsiteAnalysis

    return {
        'total_keywords': Keyword.query.count(),
        'total_results': SearchResult.query.count(),
        'total_analyses': WebsiteAnalysis.query.count(),
        'pending_scrapes': Keyword.query.filter_by(status='pending').count(),
        'completed_scrapes': Keyword.query.filter_by(status='completed').count(),
        'average_website_score': db.session.query(db.func.avg(WebsiteAnalysis.score)).scalar() or 0
    }


def get_performance_metrics():
    """Get system performance metrics"""
    return {
        'scraping_success_rate': calculate_scraping_success_rate(),
        'analysis_success_rate': calculate_analysis_success_rate(),
        'average_scraping_time': get_average_scraping_time(),
        'system_uptime': get_system_uptime()
    }


def get_recent_activity():
    """Get recent system activity"""
    from app.models import Keyword, SearchResult
    from datetime import datetime, timedelta

    last_24_hours = datetime.utcnow() - timedelta(hours=24)

    return {
        'recent_keywords': Keyword.query.filter(
            Keyword.created_at >= last_24_hours
        ).count(),
        'recent_results': SearchResult.query.filter(
            SearchResult.scraped_at >= last_24_hours
        ).count(),
        'recent_analyses': WebsiteAnalysis.query.filter(
            WebsiteAnalysis.last_analyzed >= last_24_hours
        ).count()
    }


def get_upcoming_tasks():
    """Get upcoming scheduled tasks"""
    return scheduler_service.get_scheduled_tasks()