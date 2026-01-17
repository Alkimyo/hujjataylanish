"""
Celery Tasks for Background Processing
"""

from celery import shared_task
import time
from datetime import timedelta
from django.utils import timezone
from .services import ApprovalWorkflowService
from django.db.models import Q
from .models import Hujjat, ApprovalStep, JobRun


def _mark_job_start(task_name):
    JobRun.objects.update_or_create(
        task_name=task_name,
        defaults={
            'last_status': 'running',
            'last_run_at': timezone.now(),
            'last_error': '',
        },
    )


def _mark_job_success(task_name, started_at):
    duration_ms = int((time.monotonic() - started_at) * 1000)
    JobRun.objects.update_or_create(
        task_name=task_name,
        defaults={
            'last_status': 'success',
            'last_success_at': timezone.now(),
            'last_duration_ms': duration_ms,
            'last_error': '',
        },
    )


def _mark_job_failure(task_name, started_at, error_message):
    duration_ms = int((time.monotonic() - started_at) * 1000)
    JobRun.objects.update_or_create(
        task_name=task_name,
        defaults={
            'last_status': 'failed',
            'last_duration_ms': duration_ms,
            'last_error': error_message[:1000],
        },
    )


@shared_task
def auto_approve_overdue_documents():
    """
    Task to automatically approve documents where deadline has passed
    Run this task every hour via Celery Beat
    """
    task_name = 'documents.tasks.auto_approve_overdue_documents'
    started_at = time.monotonic()
    _mark_job_start(task_name)

    try:
        auto_approved = ApprovalWorkflowService.auto_approve_overdue_documents()
        _mark_job_success(task_name, started_at)
    except Exception as exc:
        _mark_job_failure(task_name, started_at, str(exc))
        raise
    
    return {
        'task': 'auto_approve_overdue_documents',
        'timestamp': timezone.now().isoformat(),
        'auto_approved_count': auto_approved.get('approved_steps', 0),
        'skipped_steps': auto_approved.get('skipped_steps', 0),
        'status': auto_approved.get('status'),
    }


@shared_task
def send_deadline_reminders():
    """
    Task to send deadline reminders for documents approaching deadline (24 hours)
    Run this task every 6 hours via Celery Beat
    """
    task_name = 'documents.tasks.send_deadline_reminders'
    started_at = time.monotonic()
    _mark_job_start(task_name)

    try:
        result = ApprovalWorkflowService.check_and_notify_upcoming_deadlines()
        _mark_job_success(task_name, started_at)
    except Exception as exc:
        _mark_job_failure(task_name, started_at, str(exc))
        raise
    
    return {
        'task': 'send_deadline_reminders',
        'timestamp': timezone.now().isoformat(),
        'status': result.get('status'),
        'notified_24h': result.get('notified_24h', 0),
        'notified_2h': result.get('notified_2h', 0),
    }


@shared_task
def generate_qr_codes_batch():
    """
    Task to generate QR codes for approved documents that don't have them yet
    This can be run as a one-time task or scheduled
    """
    task_name = 'documents.tasks.generate_qr_codes_batch'
    started_at = time.monotonic()
    _mark_job_start(task_name)

    try:
        from .qr_service import QRCodeService

        # Find approved documents without QR codes
        documents_without_qr = Hujjat.objects.filter(status='approved').filter(
            Q(qr_code_image__isnull=True) | Q(qr_code_image='')
        )

        generated_count = 0

        for document in documents_without_qr:
            try:
                QRCodeService.save_qr_image(document)
                generated_count += 1
            except Exception as e:
                print(f"Failed to generate QR for document {document.id}: {str(e)}")

        _mark_job_success(task_name, started_at)
        return {
            'task': 'generate_qr_codes_batch',
            'timestamp': timezone.now().isoformat(),
            'generated_count': generated_count,
        }
    except Exception as exc:
        _mark_job_failure(task_name, started_at, str(exc))
        raise


@shared_task
def generate_final_pdfs_batch():
    """
    Task to generate final PDFs with QR codes for approved documents
    """
    task_name = 'documents.tasks.generate_final_pdfs_batch'
    started_at = time.monotonic()
    _mark_job_start(task_name)

    try:
        from .qr_service import QRCodeService

        # Find approved documents without final PDFs
        documents_without_pdf = Hujjat.objects.filter(status='approved').filter(
            Q(final_pdf__isnull=True) | Q(final_pdf='')
        )

        generated_count = 0
        failed_count = 0

        for document in documents_without_pdf:
            try:
                QRCodeService.generate_final_pdf(document)
                generated_count += 1
            except Exception as e:
                print(f"Failed to generate PDF for document {document.id}: {str(e)}")
                failed_count += 1

        _mark_job_success(task_name, started_at)
        return {
            'task': 'generate_final_pdfs_batch',
            'timestamp': timezone.now().isoformat(),
            'generated_count': generated_count,
            'failed_count': failed_count,
        }
    except Exception as exc:
        _mark_job_failure(task_name, started_at, str(exc))
        raise


@shared_task
def cleanup_old_notifications(days=90):
    """
    Task to clean up old read notifications
    Run this task daily via Celery Beat
    
    Args:
        days: Number of days to keep read notifications
    """
    task_name = 'documents.tasks.cleanup_old_notifications'
    started_at = time.monotonic()
    _mark_job_start(task_name)

    try:
        from .models import Notification

        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_count, _ = Notification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date
        ).delete()

        _mark_job_success(task_name, started_at)
        return {
            'task': 'cleanup_old_notifications',
            'timestamp': timezone.now().isoformat(),
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
        }
    except Exception as exc:
        _mark_job_failure(task_name, started_at, str(exc))
        raise


@shared_task
def send_daily_summary_emails():
    """
    Task to send daily summary emails to users with pending approvals
    Run this task daily at 9 AM via Celery Beat
    """
    task_name = 'documents.tasks.send_daily_summary_emails'
    started_at = time.monotonic()
    _mark_job_start(task_name)

    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from .models import User

        sent_count = 0

        # Find users with pending approvals
        users_with_pending = User.objects.filter(
            approval_tasks__status='pending'
        ).distinct()

        for user in users_with_pending:
            if not user.email_notifications:
                continue

            pending_count = ApprovalStep.objects.filter(
                approver=user,
                status='pending'
            ).count()

            if pending_count > 0:
                subject = f"Daily Summary: {pending_count} document(s) pending your approval"
                message = f"""
Hello {user.get_full_name()},

You have {pending_count} document(s) waiting for your approval.

Please log in to the system to review and approve these documents:
{settings.SITE_URL}/approvals/pending/

Best regards,
Hujjat Workflow System
                """.strip()

                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    sent_count += 1
                except Exception as e:
                    print(f"Failed to send email to {user.email}: {str(e)}")

        _mark_job_success(task_name, started_at)
        return {
            'task': 'send_daily_summary_emails',
            'timestamp': timezone.now().isoformat(),
            'sent_count': sent_count,
        }
    except Exception as exc:
        _mark_job_failure(task_name, started_at, str(exc))
        raise


# Celery Beat Schedule Configuration
# Add this to your celery.py file:

"""
from celery.schedules import crontab

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
"""
