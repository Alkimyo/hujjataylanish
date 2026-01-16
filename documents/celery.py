from celery import Celery
from celery.schedules import crontab

app = Celery('university_workflow')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Scheduled Tasks
app.conf.beat_schedule = {
    'auto-approve-overdue-hourly': {
        'task': 'documents.tasks.auto_approve_overdue_documents',
        'schedule': crontab(minute=0),  # Every hour
    },
    'send-deadline-reminders': {
        'task': 'documents.tasks.send_deadline_reminders',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    'cleanup-old-notifications': {
        'task': 'documents.tasks.cleanup_old_notifications',
        'schedule': crontab(minute=0, hour=2),  # Daily at 2 AM
    },
    'send-daily-summaries': {
        'task': 'documents.tasks.send_daily_summary_emails',
        'schedule': crontab(minute=0, hour=9),  # Daily at 9 AM
    },
}