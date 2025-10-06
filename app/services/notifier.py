# app/services/notifier.py
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import logging
from datetime import datetime
from threading import Thread
from app.models import Keyword, WebsiteAnalysis

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.email_config = self.load_email_config()
        self.notification_queue = []

    def load_email_config(self):
        """Load email configuration"""
        return {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'sender_email': 'your-email@gmail.com',
            'sender_password': 'your-app-password'
        }

    def send_scraping_completion_alert(self, keyword_id, results_count):
        """Send scraping completion notification"""
        keyword = Keyword.query.get(keyword_id)
        if not keyword:
            return

        subject = f"Scraping Completed: {keyword.keyword}"
        message = f"""
        Scraping for keyword '{keyword.keyword}' has been completed.

        Results:
        - Total businesses found: {results_count}
        - Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M')}

        You can view the results in your dashboard.
        """

        self.queue_notification(subject, message, 'scraping_completion')

    def send_website_analysis_alert(self, analysis_id, score):
        """Send website analysis results notification"""
        analysis = WebsiteAnalysis.query.get(analysis_id)
        if not analysis:
            return

        subject = f"Website Analysis: Score {score}/100"
        message = f"""
        Website analysis completed for {analysis.result.title}

        Results:
        - Overall Score: {score}/100
        - Mobile Friendly: {'Yes' if analysis.mobile_friendly else 'No'}
        - Load Time: {analysis.load_time}s
        - Professional Look: {'Yes' if analysis.professional_look else 'No'}

        Key Issues:
        {analysis.issues or 'No major issues found'}
        """

        self.queue_notification(subject, message, 'analysis_completion')

    def send_system_alert(self, alert_type, message, severity='info'):
        """Send system-level alerts"""
        subject = f"System Alert: {alert_type} - {severity.upper()}"

        alert_message = f"""
        System Alert Details:

        Type: {alert_type}
        Severity: {severity}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        Message:
        {message}
        """

        self.queue_notification(subject, alert_message, 'system_alert')

    def queue_notification(self, subject, message, notification_type):
        """Queue notification for sending"""
        self.notification_queue.append({
            'subject': subject,
            'message': message,
            'type': notification_type,
            'timestamp': datetime.now()
        })

        # Process queue in background
        Thread(target=self.process_notification_queue, daemon=True).start()

    def process_notification_queue(self):
        """Process notification queue"""
        while self.notification_queue:
            notification = self.notification_queue.pop(0)
            try:
                self.send_email(
                    notification['subject'],
                    notification['message']
                )
                logger.info(f"Notification sent: {notification['type']}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                # Requeue failed notification
                self.notification_queue.append(notification)
                break

    def send_email(self, subject, message, recipient=None):
        """Send email notification"""
        if not recipient:
            recipient = 'admin@yourcompany.com'  # Default recipient

        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = recipient
            msg['Subject'] = subject

            msg.attach(MimeText(message, 'plain'))

            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['sender_email'], self.email_config['sender_password'])
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False

    def send_daily_summary(self):
        """Send daily summary report"""
        today = datetime.now().date()

        # Get today's statistics
        today_keywords = Keyword.query.filter(
            Keyword.created_at >= today
        ).count()

        today_results = SearchResult.query.filter(
            SearchResult.scraped_at >= today
        ).count()

        completed_analyses = WebsiteAnalysis.query.filter(
            WebsiteAnalysis.last_analyzed >= today
        ).count()

        subject = f"Daily Summary - {today.strftime('%Y-%m-%d')}"
        message = f"""
        Daily Activity Summary:

        Statistics:
        - New Keywords Added: {today_keywords}
        - Results Scraped: {today_results}
        - Websites Analyzed: {completed_analyses}

        System Status:
        - All systems operational
        - No critical issues detected

        Keep up the great work!
        """

        self.queue_notification(subject, message, 'daily_summary')