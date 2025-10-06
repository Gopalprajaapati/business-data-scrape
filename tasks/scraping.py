# app/tasks/scraping.py
from app.tasks import celery, logger
from app.services.scraper import AdvancedScraperService
from app.services.notifier import NotificationService
from app.models import Keyword, SearchResult, db
from app.monitoring import monitor_scraping
import time


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
@monitor_scraping
def scrape_keyword_task(self, keyword_id):
    """Background task for scraping a keyword"""
    task_id = self.request.id

    try:
        logger.logger.info(f"Starting scraping task for keyword {keyword_id} [Task: {task_id}]")

        # Update keyword status
        keyword = Keyword.query.get(keyword_id)
        if not keyword:
            raise ValueError(f"Keyword {keyword_id} not found")

        keyword.status = 'in_progress'
        db.session.commit()

        # Perform scraping
        scraper = AdvancedScraperService()
        results = scraper.scrape_google_maps_advanced(keyword.keyword)

        # Save results
        saved_count = 0
        for result_data in results:
            result = SearchResult(**result_data)
            db.session.add(result)
            saved_count += 1

        # Update keyword status
        keyword.status = 'completed'
        keyword.last_scraped = db.func.now()
        keyword.total_results = saved_count
        db.session.commit()

        # Send notification
        notifier = NotificationService()
        notifier.send_scraping_completion_alert(keyword_id, saved_count)

        logger.logger.info(f"Scraping completed for keyword {keyword_id}: {saved_count} results")

        return {
            'keyword_id': keyword_id,
            'results_count': saved_count,
            'status': 'completed'
        }

    except Exception as e:
        logger.logger.error(f"Scraping task failed for keyword {keyword_id}: {str(e)}")

        # Update keyword status
        keyword = Keyword.query.get(keyword_id)
        if keyword:
            keyword.status = 'error'
            db.session.commit()

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.logger.info(f"Retrying scraping task for keyword {keyword_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        else:
            # Send failure notification
            notifier = NotificationService()
            notifier.send_system_alert(
                'scraping_failure',
                f"Scraping failed for keyword '{keyword.keyword if keyword else keyword_id}' after {self.max_retries} retries: {str(e)}",
                'error'
            )

            return {
                'keyword_id': keyword_id,
                'error': str(e),
                'status': 'failed'
            }


@celery.task(bind=True)
def batch_scraping_task(self, keyword_ids, priority='medium'):
    """Batch scraping task for multiple keywords"""
    task_id = self.request.id
    total_keywords = len(keyword_ids)
    completed = 0
    failed = 0

    logger.logger.info(f"Starting batch scraping for {total_keywords} keywords [Task: {task_id}]")

    results = []
    for keyword_id in keyword_ids:
        try:
            # Chain individual scraping tasks
            result = scrape_keyword_task.apply_async(
                args=[keyword_id],
                queue='scraping',
                priority=self.get_priority_value(priority)
            )
            results.append(result)

        except Exception as e:
            logger.logger.error(f"Failed to queue keyword {keyword_id}: {str(e)}")
            failed += 1

        # Update progress
        completed += 1
        self.update_state(
            state='PROGRESS',
            meta={
                'current': completed,
                'total': total_keywords,
                'status': f'Processing {completed}/{total_keywords}',
                'failed': failed
            }
        )

    return {
        'total_keywords': total_keywords,
        'completed': completed,
        'failed': failed,
        'task_ids': [r.id for r in results]
    }

    def get_priority_value(self, priority):
        """Convert priority string to Celery priority value"""
        priorities = {
            'high': 0,
            'medium': 5,
            'low': 9
        }
        return priorities.get(priority, 5)