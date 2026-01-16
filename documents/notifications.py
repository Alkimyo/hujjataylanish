
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Notification


class NotificationService:
    
    @classmethod
    def notify_approval_needed(cls, document, approver):
        
        title = f"Document Approval Needed: {document.file_name}"
        message = (
            f"You have a new document waiting for your approval.\n\n"
            f"Document: {document.file_name}\n"
            f"Type: {document.document_type.name}\n"
            f"Uploaded by: {document.uploaded_by.get_full_name()}\n"
            f"Department: {document.uploaded_by.department.name if document.uploaded_by.department else 'N/A'}\n\n"
            f"Please review and approve or reject this document at your earliest convenience."
        )
        
        notification = Notification.objects.create(
            recipient=approver,
            notification_type='approval_needed',
            title=title,
            message=message,
            document=document
        )
        
        # Send email if user has enabled email notifications
        if approver.email_notifications:
            cls._send_email(
                to_email=approver.email,
                subject=title,
                message=message,
                notification_type='approval_needed',
                document=document
            )
            notification.sent_email = True
            notification.save()
        
        # Send push notification if enabled
        if approver.push_notifications:
            cls._send_push_notification(approver, title, message)
            notification.sent_push = True
            notification.save()
    
    @classmethod
    def notify_document_approved(cls, document):
       
        uploader = document.uploaded_by
        
        title = f"Document Approved: {document.file_name}"
        message = (
            f"Great news! Your document has been fully approved.\n\n"
            f"Document: {document.file_name}\n"
            f"Type: {document.document_type.name}\n"
            f"Approved on: {document.completed_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"You can now download the official version with QR code verification."
        )
        
        notification = Notification.objects.create(
            recipient=uploader,
            notification_type='document_approved',
            title=title,
            message=message,
            document=document
        )
        
        if uploader.email_notifications:
            cls._send_email(
                to_email=uploader.email,
                subject=title,
                message=message,
                notification_type='document_approved',
                document=document
            )
            notification.sent_email = True
            notification.save()
        
        if uploader.push_notifications:
            cls._send_push_notification(uploader, title, message)
            notification.sent_push = True
            notification.save()
    
    @classmethod
    def notify_document_rejected(cls, document, rejected_by, reason):
       
        uploader = document.uploaded_by
        
        title = f"Document Rejected: {document.file_name}"
        message = (
            f"Your document has been rejected and requires revision.\n\n"
            f"Document: {document.file_name}\n"
            f"Type: {document.document_type.name}\n"
            f"Rejected by: {rejected_by.get_full_name()} ({rejected_by.get_role_display()})\n"
            f"Rejection Date: {document.completed_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"Reason:\n{reason}\n\n"
            f"Please review the feedback and resubmit your document."
        )
        
        notification = Notification.objects.create(
            recipient=uploader,
            notification_type='document_rejected',
            title=title,
            message=message,
            document=document
        )
        
        if uploader.email_notifications:
            cls._send_email(
                to_email=uploader.email,
                subject=title,
                message=message,
                notification_type='document_rejected',
                document=document
            )
            notification.sent_email = True
            notification.save()
        
        if uploader.push_notifications:
            cls._send_push_notification(uploader, title, message)
            notification.sent_push = True
            notification.save()
    
    @classmethod
    def notify_auto_approved(cls, document, missed_approver):
      
        title = f"Document Auto-Approved: {document.file_name}"
        message = (
            f"A document assigned to you was automatically approved due to deadline expiration.\n\n"
            f"Document: {document.file_name}\n"
            f"Type: {document.document_type.name}\n"
            f"Uploaded by: {document.uploaded_by.get_full_name()}\n\n"
            f"Please note that future timely responses are expected to maintain workflow efficiency."
        )
        
        notification = Notification.objects.create(
            recipient=missed_approver,
            notification_type='auto_approved',
            title=title,
            message=message,
            document=document
        )
        
        if missed_approver.email_notifications:
            cls._send_email(
                to_email=missed_approver.email,
                subject=title,
                message=message,
                notification_type='auto_approved',
                document=document
            )
            notification.sent_email = True
            notification.save()
    
    @staticmethod
    def _send_email(to_email, subject, message, notification_type, document=None):
        
        try:
            # You can use HTML templates for better formatting
            html_message = render_to_string('emails/notification.html', {
                'subject': subject,
                'message': message,
                'notification_type': notification_type,
                'document': document,
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            }) if document else None
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log error but don't fail the entire operation
            print(f"Email sending failed: {str(e)}")
    
    @staticmethod
    def _send_push_notification(user, title, message):
       
        # Implement push notification logic here
        # This could use Firebase Cloud Messaging, OneSignal, or another service
        # Example structure:
        
        try:
            # Example with Firebase (pseudo-code)
            # from firebase_admin import messaging
            # 
            # notification = messaging.Notification(
            #     title=title,
            #     body=message[:100]  # Truncate for push
            # )
            # 
            # message = messaging.Message(
            #     notification=notification,
            #     token=user.fcm_token,  # Assuming you store FCM token
            # )
            # 
            # messaging.send(message)
            
            pass
        except Exception as e:
            print(f"Push notification failed: {str(e)}")
    
    @classmethod
    def get_unread_count(cls, user):
        """
        Get count of unread notifications for a user
        
        Args:
            user: User object
        
        Returns:
            int: Count of unread notifications
        """
        return Notification.objects.filter(recipient=user, is_read=False).count()
    
    @classmethod
    def mark_as_read(cls, notification_id, user):
       
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
    
    @classmethod
    def mark_all_as_read(cls, user):
        
        Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)

    
    @staticmethod
    def notify_deadline_approaching(
        document,
        approver,
        remaining_hours,
        remaining_minutes=0,
        is_urgent=False,
        notification_type=None,
    ):
        """
        Deadline yaqinlashganligi haqida xabar.
        
        Args:
            document: Document object
            approver: User object (tasdiqlovchi)
            remaining_hours: Qolgan soatlar
            remaining_minutes: Qolgan daqiqalar
            is_urgent: Urgent xabarmi?
            notification_type: Xabar turi
        """
        from .models import Notification
        
        if is_urgent:
            title = f"⏰ URGENT: Hujjat tasdiqlash muddati tez orada tugaydi!"
            message = (
                f"Sizda tasdiqlash uchun qoldirilgan '{document.title}' hujjati "
                f"uchun faqat {remaining_hours} soat {remaining_minutes} daqiqa qoldi! "
                f"Iltimos, darhol ko'rib chiqing."
            )
            notification_type = notification_type or 'deadline_urgent'
        else:
            title = f"📅 Eslatma: Hujjat tasdiqlash muddati yaqinlashmoqda"
            message = (
                f"Sizda tasdiqlash uchun qoldirilgan '{document.title}' hujjati "
                f"uchun {remaining_hours} soat qoldi."
            )
            notification_type = notification_type or 'deadline_reminder'
        
        # Notification yaratish
        Notification.objects.create(
            recipient=approver,
            document=document,
            title=title,
            message=message,
            notification_type=notification_type,
            is_urgent=is_urgent
        )
        
        # Email yuborish (agar sozlamalarda yoqilgan bo'lsa)
        if approver.email:
            try:
                from django.core.mail import send_mail
                send_mail(
                    subject=title,
                    message=message,
                    from_email='noreply@unidocs.uz',
                    recipient_list=[approver.email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Email notification error: {e}")
        
        print(f"DEADLINE NOTIFICATION: Sent to {approver.get_full_name()}")

    @classmethod
    def notify_deadline_batch(
        cls,
        approver,
        documents,
        remaining_hours,
        remaining_minutes=0,
        is_urgent=False,
        notification_type=None,
    ):
        if not documents:
            return

        if is_urgent:
            title = "⏰ URGENT: Bir nechta hujjatlarning muddati tugash arafasida"
            time_text = f"{remaining_hours} soat {remaining_minutes} daqiqa"
        else:
            title = "📅 Eslatma: Bir nechta hujjatlarning muddati yaqinlashmoqda"
            time_text = f"{remaining_hours} soat"

        document_names = [doc.title or doc.file_name for doc in documents[:5]]
        more_count = max(len(documents) - len(document_names), 0)
        list_text = "\n".join([f"- {name}" for name in document_names])
        if more_count:
            list_text += f"\n- va yana {more_count} ta"

        message = (
            f"Sizda tasdiqlash uchun {len(documents)} ta hujjat bor.\n"
            f"Qolgan vaqt: {time_text}\n\n"
            f"{list_text}"
        )

        notification_type = notification_type or ('deadline_urgent' if is_urgent else 'deadline_reminder')

        Notification.objects.create(
            recipient=approver,
            title=title,
            message=message,
            notification_type=notification_type,
            is_urgent=is_urgent,
        )

        if approver.email:
            try:
                from django.core.mail import send_mail
                send_mail(
                    subject=title,
                    message=message,
                    from_email='noreply@unidocs.uz',
                    recipient_list=[approver.email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Email notification error: {e}")

    @classmethod
    def notify_author_about_urgent_deadline(cls, document, remaining_hours, remaining_minutes=0):
        uploader = document.uploaded_by
        title = "⏰ URGENT: Hujjat tasdiqlash muddati tugash arafasida"
        message = (
            f"Siz yuklagan '{document.title}' hujjati "
            f"bo'yicha tasdiqlashga {remaining_hours} soat {remaining_minutes} daqiqa qoldi.\n"
            "Iltimos, jarayonni kuzatib boring."
        )

        notification = Notification.objects.create(
            recipient=uploader,
            notification_type='deadline_urgent',
            title=title,
            message=message,
            document=document,
            is_urgent=True,
        )

        if uploader.email_notifications and uploader.email:
            cls._send_email(
                to_email=uploader.email,
                subject=title,
                message=message,
                notification_type='deadline_urgent',
                document=document,
            )
            notification.sent_email = True
            notification.save()
    
   
