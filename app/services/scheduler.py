# app/services/scheduler.py
import schedule
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from app.models import Keyword, SearchResult
from app.services.scraper import AdvancedScraperService

logger = logging.getLogger(__name__)


class IntelligentScheduler:
    def __init__(self):
        self.scheduled_tasks = defaultdict(list)
        self.scraper_service = AdvancedScraperService()
        self.performance_metrics = {}
        self.is_running = False

    def start_scheduler(self):
        """Start the intelligent scheduling system"""
        self.is_running = True
        scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Intelligent scheduler started")

    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    def schedule_optimal_scraping(self, keyword_id, priority='medium'):
        """Schedule scraping at optimal time"""
        keyword = Keyword.query.get(keyword_id)
        if not keyword:
            return False

        optimal_time = self.calculate_optimal_time(keyword, priority)
        task_id = f"scrape_{keyword_id}_{datetime.now().timestamp()}"

        # Schedule the task
        schedule.every().day.at(optimal_time).do(
            self.execute_scheduled_scraping,
            keyword_id=keyword_id,
            task_id=task_id
        ).tag(task_id)

        # Store task metadata
        self.scheduled_tasks[keyword_id].append({
            'task_id': task_id,
            'scheduled_time': optimal_time,
            'priority': priority,
            'status': 'scheduled'
        })

        logger.info(f"Scheduled scraping for '{keyword.keyword}' at {optimal_time}")
        return True

    def calculate_optimal_time(self, keyword, priority):
        """Calculate optimal scraping time based on historical data"""
        base_hour = self.get_base_scraping_time(priority)

        # Adjust based on keyword characteristics
        adjustment = self.calculate_keyword_adjustment(keyword)
        adjusted_hour = (base_hour + adjustment) % 24

        # Add random minute to avoid pattern detection
        random_minute = hash(keyword.keyword) % 60

        return f"{adjusted_hour:02d}:{random_minute:02d}"

    def get_base_scraping_time(self, priority):
        """Get base scraping time based on priority"""
        priority_times = {
            'high': 2,  # 2 AM - Low traffic
            'medium': 4,  # 4 AM
            'low': 6  # 6 AM
        }
        return priority_times.get(priority, 4)

    def calculate_keyword_adjustment(self, keyword):
        """Calculate time adjustment based on keyword characteristics"""
        adjustment = 0

        # Analyze previous scraping performance
        previous_results = SearchResult.query.filter_by(keyword_id=keyword.id).all()

        if previous_results:
            # Adjust based on success rate
            success_rate = self.calculate_success_rate(previous_results)
            if success_rate < 0.5:
                adjustment += 2  # Try different time if low success

        # Adjust based on keyword complexity
        word_count = len(keyword.keyword.split())
        if word_count > 3:
            adjustment -= 1  # Complex keywords might need different timing

        return adjustment

    def execute_scheduled_scraping(self, keyword_id, task_id):
        """Execute scheduled scraping task"""
        try:
            # Update task status
            self.update_task_status(keyword_id, task_id, 'running')

            # Perform scraping
            results = self.scraper_service.scrape_google_maps_advanced(
                Keyword.query.get(keyword_id).keyword
            )

            # Update performance metrics
            self.update_performance_metrics(keyword_id, len(results))

            # Update task status
            self.update_task_status(keyword_id, task_id, 'completed')

            logger.info(f"Completed scheduled scraping for keyword {keyword_id}")

        except Exception as e:
            logger.error(f"Scheduled scraping failed for {keyword_id}: {e}")
            self.update_task_status(keyword_id, task_id, 'failed')

    def schedule_batch_processing(self, keyword_ids, batch_size=5, delay_minutes=30):
        """Schedule batch processing of multiple keywords"""
        batches = [keyword_ids[i:i + batch_size] for i in range(0, len(keyword_ids), batch_size)]

        for i, batch in enumerate(batches):
            execution_time = datetime.now() + timedelta(minutes=i * delay_minutes)
            time_str = execution_time.strftime("%H:%M")

            schedule.every().day.at(time_str).do(
                self.process_keyword_batch,
                batch=batch
            )

            logger.info(f"Scheduled batch {i + 1} for {time_str}")

    def process_keyword_batch(self, batch):
        """Process a batch of keywords"""
        for keyword_id in batch:
            self.schedule_optimal_scraping(keyword_id)

    def optimize_schedule_based_on_performance(self):
        """Optimize schedule based on historical performance"""
        performance_data = self.analyze_scraping_performance()

        for keyword_id, metrics in performance_data.items():
            if metrics['success_rate'] < 0.6:
                # Reschedule poorly performing keywords
                self.reschedule_keyword(keyword_id, metrics)

    def analyze_scraping_performance(self):
        """Analyze historical scraping performance"""
        performance_data = {}

        keywords = Keyword.query.all()
        for keyword in keywords:
            results = SearchResult.query.filter_by(keyword_id=keyword.id).all()
            success_rate = self.calculate_success_rate(results)

            performance_data[keyword.id] = {
                'success_rate': success_rate,
                'total_results': len(results),
                'average_quality': self.calculate_average_quality(results)
            }

        return performance_data

    def calculate_success_rate(self, results):
        """Calculate scraping success rate"""
        if not results:
            return 0

        successful_results = len([r for r in results if r.title and r.website])
        return successful_results / len(results)

    def calculate_average_quality(self, results):
        """Calculate average result quality"""
        if not results:
            return 0

        quality_scores = []
        for result in results:
            score = 0
            if result.title:
                score += 30
            if result.website:
                score += 30
            if result.phone:
                score += 20
            if result.stars:
                score += 20

            quality_scores.append(score)

        return sum(quality_scores) / len(quality_scores)

    def update_task_status(self, keyword_id, task_id, status):
        """Update task status in tracking"""
        for task in self.scheduled_tasks[keyword_id]:
            if task['task_id'] == task_id:
                task['status'] = status
                task['updated_at'] = datetime.now()
                break

    def update_performance_metrics(self, keyword_id, result_count):
        """Update performance metrics for scheduling optimization"""
        if keyword_id not in self.performance_metrics:
            self.performance_metrics[keyword_id] = []

        self.performance_metrics[keyword_id].append({
            'timestamp': datetime.now(),
            'result_count': result_count,
            'success': result_count > 0
        })

        # Keep only last 10 records
        if len(self.performance_metrics[keyword_id]) > 10:
            self.performance_metrics[keyword_id] = self.performance_metrics[keyword_id][-10:]

    def get_scheduled_tasks(self):
        """Get all scheduled tasks"""
        return dict(self.scheduled_tasks)

    def cancel_scheduled_task(self, keyword_id, task_id):
        """Cancel a scheduled task"""
        if keyword_id in self.scheduled_tasks:
            self.scheduled_tasks[keyword_id] = [
                task for task in self.scheduled_tasks[keyword_id]
                if task['task_id'] != task_id
            ]

            # Remove from schedule
            schedule.clear(task_id)
            return True
        return False

    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        schedule.clear()
        logger.info("Scheduler stopped")