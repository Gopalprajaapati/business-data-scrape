# app/documentation/__init__.py
from flask import Blueprint, render_template, jsonify
from flask_restx import Api, Resource, fields
from app.security import require_auth
import logging

logger = logging.getLogger(__name__)

# Create API documentation blueprint
bp = Blueprint('api_docs', __name__, url_prefix='/api/docs')

# Create RESTX API
api = Api(
    bp,
    doc='/',
    title='Business Scraper API',
    version='1.0',
    description='Comprehensive API for business data scraping and analysis',
    security='Bearer Auth',
    authorizations={
        'Bearer Auth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    }
)

# API Models for documentation
keyword_model = api.model('Keyword', {
    'id': fields.Integer(description='Keyword ID'),
    'keyword': fields.String(required=True, description='Search keyword'),
    'status': fields.String(description='Processing status'),
    'created_at': fields.DateTime(description='Creation timestamp')
})

scraping_request_model = api.model('ScrapingRequest', {
    'keyword': fields.String(required=True, description='Keyword to scrape'),
    'max_results': fields.Integer(default=50, description='Maximum results to fetch'),
    'priority': fields.String(default='medium', description='Processing priority')
})

analysis_request_model = api.model('AnalysisRequest', {
    'url': fields.String(required=True, description='Website URL to analyze'),
    'analysis_type': fields.String(default='comprehensive', description='Type of analysis')
})

report_request_model = api.model('ReportRequest', {
    'keyword_id': fields.Integer(required=True, description='Keyword ID for report'),
    'report_type': fields.String(default='executive', description='Type of report'),
    'format': fields.String(default='pdf', description='Output format')
})

# API Namespaces
scraping_ns = api.namespace('scraping', description='Scraping operations')
analysis_ns = api.namespace('analysis', description='Analysis operations')
reporting_ns = api.namespace('reporting', description='Reporting operations')
ml_ns = api.namespace('ml', description='Machine Learning operations')
admin_ns = api.namespace('admin', description='Administrative operations')


# Scraping Endpoints
@scraping_ns.route('/keywords')
class KeywordList(Resource):
    @scraping_ns.doc('list_keywords')
    @scraping_ns.marshal_list_with(keyword_model)
    @require_auth
    def get(self):
        """Get all keywords"""
        from app.models import Keyword
        return Keyword.query.all()

    @scraping_ns.doc('create_keyword')
    @scraping_ns.expect(scraping_request_model)
    @scraping_ns.marshal_with(keyword_model)
    @require_auth
    def post(self):
        """Create a new keyword for scraping"""
        from app.models import Keyword, db

        data = api.payload
        keyword = Keyword(
            keyword=data['keyword'],
            status='pending'
        )
        db.session.add(keyword)
        db.session.commit()

        return keyword, 201


@scraping_ns.route('/keywords/<int:keyword_id>')
class KeywordDetail(Resource):
    @scraping_ns.doc('get_keyword')
    @scraping_ns.marshal_with(keyword_model)
    @require_auth
    def get(self, keyword_id):
        """Get a specific keyword"""
        from app.models import Keyword
        keyword = Keyword.query.get_or_404(keyword_id)
        return keyword

    @scraping_ns.doc('delete_keyword')
    @require_auth
    def delete(self, keyword_id):
        """Delete a keyword"""
        from app.models import Keyword, db

        keyword = Keyword.query.get_or_404(keyword_id)
        db.session.delete(keyword)
        db.session.commit()

        return {'message': 'Keyword deleted successfully'}


@scraping_ns.route('/scrape')
class ScrapeImmediate(Resource):
    @scraping_ns.doc('scrape_immediate')
    @scraping_ns.expect(scraping_request_model)
    @require_auth
    def post(self):
        """Scrape immediately (synchronous)"""
        from app.services.scraper import AdvancedScraperService

        data = api.payload
        scraper = AdvancedScraperService()
        results = scraper.scrape_google_maps_advanced(
            data['keyword'],
            data.get('max_results', 50)
        )

        return {
            'success': True,
            'keyword': data['keyword'],
            'results_count': len(results),
            'results': results[:10]  # Return first 10 results
        }


# Analysis Endpoints
@analysis_ns.route('/analyze')
class AnalyzeWebsite(Resource):
    @analysis_ns.doc('analyze_website')
    @analysis_ns.expect(analysis_request_model)
    @require_auth
    def post(self):
        """Analyze a website"""
        from app.services.analyzer import IntelligentWebsiteAnalyzer

        data = api.payload
        analyzer = IntelligentWebsiteAnalyzer()

        if data.get('analysis_type') == 'comprehensive':
            analysis = analyzer.comprehensive_analysis(data['url'])
        else:
            analysis = analyzer.basic_website_analysis(data['url'])

        return {
            'success': True,
            'url': data['url'],
            'analysis': analysis
        }


# Reporting Endpoints
@reporting_ns.route('/reports/generate')
class GenerateReport(Resource):
    @reporting_ns.doc('generate_report')
    @reporting_ns.expect(report_request_model)
    @require_auth
    def post(self):
        """Generate a business intelligence report"""
        from app.services.reporter import BusinessIntelligenceReporter

        data = api.payload
        reporter = BusinessIntelligenceReporter()
        report = reporter.generate_comprehensive_report(
            data['keyword_id'],
            data.get('report_type', 'executive')
        )

        if data.get('format') == 'pdf' and report:
            return {
                'success': True,
                'report_url': f'/api/reports/download/{data["keyword_id"]}.pdf'
            }
        else:
            return {
                'success': True,
                'report': report
            }


# ML Endpoints
@ml_ns.route('/predict/website-quality')
class PredictWebsiteQuality(Resource):
    @ml_ns.doc('predict_website_quality')
    @require_auth
    def post(self):
        """Predict website quality using ML"""
        from app.ml import BusinessIntelligenceML

        data = api.payload
        ml_engine = BusinessIntelligenceML()
        prediction = ml_engine.predict_website_quality(data.get('features', {}))

        return {
            'success': True,
            'prediction': prediction,
            'features_used': list(data.get('features', {}).keys())
        }


# Admin Endpoints
@admin_ns.route('/system/stats')
class SystemStats(Resource):
    @admin_ns.doc('system_stats')
    @require_auth
    def get(self):
        """Get system statistics"""
        from app.monitoring import PerformanceMonitor

        monitor = PerformanceMonitor()
        stats = monitor.get_performance_report()

        return {
            'success': True,
            'system_stats': stats
        }


@admin_ns.route('/tasks/queue')
class TaskQueue(Resource):
    @admin_ns.doc('task_queue')
    @require_auth
    def get(self):
        """Get task queue status"""
        from app.tasks import celery

        inspector = celery.control.inspect()
        active_tasks = inspector.active() or {}

        return {
            'success': True,
            'active_tasks': active_tasks
        }


# Error handlers
@api.errorhandler(404)
def handle_not_found(error):
    """Handle 404 errors"""
    return {
        'success': False,
        'error': 'Resource not found',
        'message': str(error)
    }, 404


@api.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return {
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }, 500


@api.errorhandler(401)
def handle_unauthorized(error):
    """Handle 401 errors"""
    return {
        'success': False,
        'error': 'Unauthorized',
        'message': 'Authentication required'
    }, 401


@api.errorhandler(403)
def handle_forbidden(error):
    """Handle 403 errors"""
    return {
        'success': False,
        'error': 'Forbidden',
        'message': 'Insufficient permissions'
    }, 403