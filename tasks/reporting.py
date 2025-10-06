# app/tasks/reporting.py
from app.tasks import celery, logger
from app.services.reporter import BusinessIntelligenceReporter
from app.services.notifier import NotificationService
from app.models import Keyword
import tempfile
import os
from datetime import datetime


@celery.task(bind=True)
def generate_report_task(self, keyword_id, report_type='executive', format_type='pdf', email_recipient=None):
    """Background task for report generation"""
    task_id = self.request.id

    try:
        logger.logger.info(f"Starting report generation for keyword {keyword_id} [Task: {task_id}]")

        # Generate report
        reporter = BusinessIntelligenceReporter()
        report = reporter.generate_comprehensive_report(keyword_id, report_type)

        if not report:
            raise ValueError("Failed to generate report")

        # Handle different formats
        if format_type == 'pdf':
            report_content = reporter.generate_pdf_report(report, Keyword.query.get(keyword_id))
            file_extension = 'pdf'
            content_type = 'application/pdf'
        elif format_type == 'excel':
            report_content = reporter.generate_excel_report(report, Keyword.query.get(keyword_id))
            file_extension = 'xlsx'
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            # Return JSON data
            return {
                'keyword_id': keyword_id,
                'report_type': report_type,
                'report_data': report,
                'status': 'completed'
            }

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as f:
            f.write(report_content)
            temp_file_path = f.name

        # Send email if recipient specified
        if email_recipient:
            notifier = NotificationService()
            notifier.send_email(
                subject=f"Business Intelligence Report - {Keyword.query.get(keyword_id).keyword}",
                message=f"Please find attached the {report_type} report for your analysis.",
                recipient=email_recipient,
                attachments=[temp_file_path]
            )

            # Clean up temp file
            os.unlink(temp_file_path)

        logger.logger.info(f"Report generation completed for keyword {keyword_id}")

        return {
            'keyword_id': keyword_id,
            'report_type': report_type,
            'format': format_type,
            'file_path': temp_file_path if not email_recipient else None,
            'status': 'completed'
        }

    except Exception as e:
        logger.logger.error(f"Report generation task failed for keyword {keyword_id}: {str(e)}")

        return {
            'keyword_id': keyword_id,
            'error': str(e),
            'status': 'failed'
        }


@celery.task
def generate_daily_summary_report():
    """Scheduled task for daily summary reports"""
    try:
        logger.logger.info("Generating daily summary report")

        # Get all completed keywords from yesterday
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)

        completed_keywords = Keyword.query.filter(
            Keyword.status == 'completed',
            Keyword.completed_at >= yesterday
        ).all()

        # Generate summary for each keyword
        reporter = BusinessIntelligenceReporter()
        summary_data = {}

        for keyword in completed_keywords:
            summary = reporter.generate_executive_summary(
                keyword,
                keyword.results.all(),
                []
            )
            summary_data[keyword.keyword] = summary

        # Send daily summary email
        notifier = NotificationService()
        notifier.send_daily_summary()

        logger.logger.info(f"Daily summary report generated for {len(completed_keywords)} keywords")

        return {
            'total_keywords': len(completed_keywords),
            'status': 'completed'
        }

    except Exception as e:
        logger.logger.error(f"Daily summary report generation failed: {str(e)}")
        return {
            'error': str(e),
            'status': 'failed'
        }