# app/tasks/analysis.py
from app.tasks import celery, logger
from app.services.analyzer import IntelligentWebsiteAnalyzer
from app.services.notifier import NotificationService
from app.models import SearchResult, WebsiteAnalysis, db
from app.optimization import CacheManager
import time


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def analyze_website_task(self, result_id):
    """Background task for website analysis"""
    task_id = self.request.id

    try:
        logger.logger.info(f"Starting website analysis for result {result_id} [Task: {task_id}]")

        # Get search result
        result = SearchResult.query.get(result_id)
        if not result or not result.website:
            raise ValueError(f"Result {result_id} not found or has no website")

        # Check cache first
        cache_manager = CacheManager()
        cache_key = f"analysis_{hash(result.website)}"
        cached_analysis = cache_manager.get(cache_key)

        if cached_analysis:
            logger.logger.info(f"Using cached analysis for {result.website}")
            analysis_data = cached_analysis
            is_cached = True
        else:
            # Perform fresh analysis
            analyzer = IntelligentWebsiteAnalyzer()
            analysis_data = analyzer.comprehensive_analysis(result.website)
            is_cached = False

            # Cache the analysis
            cache_manager.set(cache_key, analysis_data, 3600)  # Cache for 1 hour

        # Save analysis to database
        analysis = WebsiteAnalysis(
            result_id=result_id,
            mobile_friendly=analysis_data.get('mobile_friendly'),
            load_time=analysis_data.get('load_time'),
            professional_look=analysis_data.get('professional_look'),
            score=analysis_data.get('overall_score', 0),
            seo_score=analysis_data.get('seo_score', {}).get('seo_score', 0),
            performance_score=analysis_data.get('performance_score', {}).get('performance_score', 0),
            security_score=analysis_data.get('security_score', {}).get('security_score', 0),
            credibility_score=analysis_data.get('credibility_score', {}).get('credibility_score', 0),
            issues='|'.join(analysis_data.get('issues', [])),
            is_cached=is_cached
        )

        db.session.add(analysis)
        db.session.commit()

        # Send notification for high-quality websites
        if analysis_data.get('overall_score', 0) >= 80:
            notifier = NotificationService()
            notifier.send_website_analysis_alert(analysis.id, analysis.score)

        logger.logger.info(f"Website analysis completed for {result.website}: Score {analysis.score}")

        return {
            'result_id': result_id,
            'website': result.website,
            'score': analysis.score,
            'is_cached': is_cached,
            'status': 'completed'
        }

    except Exception as e:
        logger.logger.error(f"Website analysis task failed for result {result_id}: {str(e)}")

        if self.request.retries < self.max_retries:
            logger.logger.info(f"Retrying analysis task for result {result_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        else:
            return {
                'result_id': result_id,
                'error': str(e),
                'status': 'failed'
            }


@celery.task(bind=True)
def batch_analysis_task(self, result_ids, analysis_type='comprehensive'):
    """Batch analysis task for multiple websites"""
    task_id = self.request.id
    total_results = len(result_ids)
    completed = 0
    failed = 0

    logger.logger.info(f"Starting batch analysis for {total_results} websites [Task: {task_id}]")

    results = []
    for result_id in result_ids:
        try:
            result = analyze_website_task.apply_async(
                args=[result_id],
                queue='analysis'
            )
            results.append(result)

        except Exception as e:
            logger.logger.error(f"Failed to queue analysis for result {result_id}: {str(e)}")
            failed += 1

        # Update progress
        completed += 1
        self.update_state(
            state='PROGRESS',
            meta={
                'current': completed,
                'total': total_results,
                'status': f'Analyzing {completed}/{total_results}',
                'failed': failed
            }
        )

        # Small delay to avoid overwhelming the system
        time.sleep(1)

    return {
        'total_results': total_results,
        'completed': completed,
        'failed': failed,
        'task_ids': [r.id for r in results]
    }