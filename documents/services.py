from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q, F  # F obyekti qo'shildi (muhim!)
from . import models
from .notifications import NotificationService

class ApprovalWorkflowService:
    """Service to manage document approval workflows"""
    
    @staticmethod
    def approve_document(document_id, user, comment='', request=None):
        """Approve a document at the current step"""
        with transaction.atomic():
            # Pessimistik bloklash (bir vaqtda ikki kishi tasdiqlamasligi uchun)
            document = models.Document.objects.select_for_update().get(id=document_id)
            ApprovalWorkflowService._skip_unassigned_steps(document)
            
            current_step = document.get_current_approver()
            if not current_step:
                raise ValidationError("Tasdiqlash bosqichi topilmadi")
            
            if current_step.approver != user:
                raise PermissionDenied("Siz bu hujjatni tasdiqlash huquqiga ega emassiz")
            
            if current_step.status != 'pending':
                raise ValidationError(f"Bu bosqich allaqachon {current_step.get_status_display()} holatida")
            
            # 1. Bosqichni yangilash
            current_step.status = 'approved'
            current_step.approved_at = timezone.now()
            current_step.comment = comment
            current_step.save()
            
            # 2. Log yozish
            models.ApprovalLog.objects.create(
                document=document,
                approval_step=current_step,
                approver=user,
                action='approved',
                comment=comment,
                ip_address=ApprovalWorkflowService._get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
            )
            models.AuditLog.objects.create(
                user=user,
                action='document_approved',
                document=document,
                metadata={
                    'step_order': current_step.step_order,
                    'role_required': current_step.role_required,
                },
                ip_address=ApprovalWorkflowService._get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            )
            
            # 3. Keyingi bosqichga o'tish
            next_step_index = document.current_step + 1
            total_steps = document.approval_steps.count()
            
            if next_step_index < total_steps:
                document.current_step = next_step_index
                document.save()
                
                # Keyingi odamga xabar berish
                try:
                    next_approver_step = document.approval_steps.get(step_order=next_step_index)
                    if next_approver_step.approver:
                        NotificationService.notify_approval_needed(
                            document=document,
                            approver=next_approver_step.approver
                        )
                        next_approver_name = next_approver_step.approver.get_full_name()
                    else:
                        next_approver_name = "Noma'lum"
                except models.ApprovalStep.DoesNotExist:
                    next_approver_name = "Tizim xatosi"

                return {
                    'status': 'approved_next_step',
                    'message': f'Hujjat tasdiqlandi. Keyingi bosqich ({next_step_index + 1}/{total_steps}): {next_approver_name}',
                }
            else:
                # 4. To'liq yakunlash
                document.status = 'approved'
                document.completed_at = timezone.now()
                document.save()
                
                # QR Kod yaratish
                try:
                    from .qr_service import QRCodeService
                    QRCodeService.save_qr_image(document)
                except Exception as e:
                    print(f"QR kod yaratishda xatolik: {e}")
                
                # Muallifga xabar
                NotificationService.notify_document_approved(document)
                
                return {
                    'status': 'fully_approved',
                    'message': "Hujjat to'liq tasdiqlandi! QR kod generatsiya qilindi.",
                }
    
    @staticmethod
    def reject_document(document_id, user, reason, request=None):
        """Reject a document at the current step"""
        # Sabab uzunligini tekshirish (ixtiyoriy, kamaytirish mumkin)
        if len(reason.strip()) < 5:
            raise ValidationError("Rad etish sababi kamida 5 ta belgidan iborat bo'lishi kerak")
        
        with transaction.atomic():
            document = models.Document.objects.select_for_update().get(id=document_id)
            ApprovalWorkflowService._skip_unassigned_steps(document)
            
            current_step = document.get_current_approver()
            if not current_step:
                raise ValidationError("Tasdiqlash bosqichi topilmadi")
            
            if current_step.approver != user:
                raise PermissionDenied("Sizda rad etish huquqi yo'q")
            
            if current_step.status != 'pending':
                raise ValidationError(f"Bu bosqich allaqachon {current_step.status} holatida")
            
            # 1. Bosqichni rad etish
            current_step.status = 'rejected'
            current_step.approved_at = timezone.now()
            current_step.comment = reason
            current_step.save()
            
            # 2. Log
            models.ApprovalLog.objects.create(
                document=document,
                approval_step=current_step,
                approver=user,
                action='rejected',
                comment=reason,
                ip_address=ApprovalWorkflowService._get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
            )
            models.AuditLog.objects.create(
                user=user,
                action='document_rejected',
                document=document,
                metadata={
                    'step_order': current_step.step_order,
                    'role_required': current_step.role_required,
                    'reason': reason,
                },
                ip_address=ApprovalWorkflowService._get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            )
            
            # 3. Hujjatni rad etish
            document.status = 'rejected'
            document.completed_at = timezone.now()
            document.save()
            
            # Xabar
            NotificationService.notify_document_rejected(document, user, reason)
            
            return {
                'status': 'rejected',
                'message': 'Hujjat rad etildi va muallifga qaytarildi',
                'rejected_by': user.get_full_name(),
            }
    
    @staticmethod
    def get_pending_approvals_for_user(user):
        """
        Foydalanuvchi uchun kutilayotgan tasdiqlarni qaytaradi.
        MUHIM: Faqat hujjatning HOZIRGI bosqichi foydalanuvchiga tegishli bo'lsa ko'rsatiladi.
        """
        return models.ApprovalStep.objects.filter(
            approver=user,
            status='pending',
            document__status='pending_approval',
            # MUHIM TUZATISH: Step order hujjatning current_stepiga teng bo'lishi shart
            step_order=F('document__current_step')
        ).select_related(
            'document', 
            'document__uploaded_by', 
            'document__document_type'
        ).order_by('deadline')
    
    @staticmethod
    def get_document_history(document):
        steps = []
        for step in document.approval_steps.all().order_by('step_order'):
            step_info = {
                'order': step.step_order + 1,
                'role': dict(models.Role.ROLE_TYPE_CHOICES).get(step.role_required, step.role_required),
                'approver': step.approver.get_full_name() if step.approver else 'Biriktirilmagan',
                'status': step.get_status_display(),
                'deadline': step.deadline,
                'approved_at': step.approved_at,
                'comment': step.comment,
                # Hozirgi aktiv bosqichmi?
                'is_current': step.step_order == document.current_step and document.status == 'pending_approval',
            }
            
            # Loglarni qo'shish
            logs = models.ApprovalLog.objects.filter(approval_step=step).order_by('-timestamp')
            step_info['logs'] = [{
                'action': log.get_action_display(),
                'timestamp': log.timestamp,
                'comment': log.comment,
                'user': log.approver.get_full_name()
            } for log in logs]
            
            steps.append(step_info)
        
        return {
            'document': document,
            'status': document.get_status_display(),
            'uploaded_at': document.uploaded_at,
            'completed_at': document.completed_at,
            'steps': steps,
            'current_step_text': document.get_expected_approver_text(),
        }
    
    @staticmethod
    def _get_client_ip(request):
        if not request: return None
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def _skip_unassigned_steps(document):
        """
        If current step has no approver, mark as skipped and advance.
        This prevents workflows from getting stuck on unassigned approvers.
        """
        now = timezone.now()
        updated = False

        while True:
            current_step = document.get_current_approver()
            if not current_step:
                break
            if current_step.status != 'pending' or current_step.approver is not None:
                break

            current_step.status = 'skipped'
            current_step.approved_at = now
            current_step.comment = "Auto-skipped: approver not found"
            current_step.save(update_fields=['status', 'approved_at', 'comment'])

            next_step_index = document.current_step + 1
            total_steps = document.approval_steps.count()

            if next_step_index < total_steps:
                document.current_step = next_step_index
                document.save(update_fields=['current_step'])
                updated = True
                continue

            document.status = 'approved'
            document.completed_at = now
            document.save(update_fields=['status', 'completed_at'])
            updated = True
            break

        return updated
    
    # Sozlamalar
    DEFAULT_APPROVAL_DEADLINE_HOURS = 48  # 2 kun = 48 soat
    AUTO_APPROVE_AFTER_DEADLINE = True   # Deadline tugagach avtomatik tasdiqlash
    NOTIFY_BEFORE_24H = True             # 24 soat oldin eslatish
    NOTIFY_BEFORE_2H = True              # 2 soat oldin eslatish
    NIGHT_HOURS = (23, 6)                # Kechasi (23:00 - 06:00)
    EARLY_NOTIFY_HOUR = 21               # Kechasi bo'lsa, 21:00 da eslatish
    
    @staticmethod
    def auto_approve_overdue_documents():
        """
        Muddati o'tgan hujjatlarni avtomatik tasdiqlash.
        Har soat yarim soatda bir chaqiriladi.
        """
        from datetime import timedelta
        from django.utils import timezone
        from .models import Document, ApprovalStep, ApprovalLog
        
        now = timezone.now()
        
        with transaction.atomic():
            # Muddati o'tgan bosqichlarni topish
            overdue_steps = ApprovalStep.objects.filter(
                status='pending',
                deadline__lt=now,  # Deadline o'tgan
                document__status='pending_approval',
                step_order=F('document__current_step')
            ).select_for_update().select_related('document', 'approver')
            
            approved_count = 0
            skipped_count = 0
            
            for step in overdue_steps:
                try:
                    document = step.document
                    
                    # Deadline necha soat o'tganligini hisoblash
                    hours_overdue = (now - step.deadline).total_seconds() / 3600
                    
                    # 1. Bosqichni avtomatik tasdiqlash
                    step.status = 'approved'
                    step.approved_at = now
                    step.comment = f"Avtomatik tasdiqlandi (deadline {hours_overdue:.1f} soat o'tgach)"
                    step.save()
                    
                    # 2. Log yozish
                    ApprovalLog.objects.create(
                        document=document,
                        approval_step=step,
                        approver=step.approver if step.approver else None,
                        action='auto_approved',
                        comment=f"Hujjat deadline tugagandan keyin avtomatik tasdiqlandi. Kechikish: {hours_overdue:.1f} soat",
                        ip_address=None,
                        user_agent='Auto-approval System'
                    )
                    
                    # 3. Keyingi bosqichga o'tish yoki yakunlash
                    next_step_index = document.current_step + 1
                    total_steps = document.approval_steps.count()
                    
                    if next_step_index < total_steps:
                        # Keyingi bosqichga o'tish
                        document.current_step = next_step_index
                        document.save()
                        
                        # Keyingi tasdiqlovchiga xabar
                        try:
                            next_step = document.approval_steps.get(step_order=next_step_index)
                            if next_step.approver:
                                # Yangi deadline o'rnatish (2 kun)
                                next_step.deadline = now + timedelta(
                                    hours=ApprovalWorkflowService.DEFAULT_APPROVAL_DEADLINE_HOURS
                                )
                                next_step.save()
                                
                                NotificationService.notify_approval_needed(
                                    document=document,
                                    approver=next_step.approver
                                )
                        except ApprovalStep.DoesNotExist:
                            pass
                        
                    else:
                        # To'liq yakunlash
                        document.status = 'approved'
                        document.completed_at = now
                        document.save()
                        
                        # QR Kod yaratish
                        try:
                            from .qr_service import QRCodeService
                            QRCodeService.save_qr_image(document)
                        except Exception as e:
                            print(f"QR kod yaratishda xatolik: {e}")
                        
                        # Muallifga xabar
                        NotificationService.notify_document_approved(document)
                    
                    approved_count += 1
                    
                    # System log
                    print(f"AUTO-APPROVED: Document {document.id} step {step.step_order + 1} "
                          f"approved after {hours_overdue:.1f} hours overdue")
                    
                except Exception as e:
                    skipped_count += 1
                    print(f"AUTO-APPROVE ERROR: {e}")
                    continue
            
            return {
                'status': 'completed',
                'approved_steps': approved_count,
                'skipped_steps': skipped_count,
                'timestamp': now
            }
    
    @staticmethod
    def check_and_notify_upcoming_deadlines():
        """
        Deadline yaqinlashayotgan bosqichlar haqida aqlli ogohlantirish xabarlari yuborish.
        Har 30 daqiqada chaqiriladi.
        """
        from datetime import timedelta
        from django.utils import timezone
        
        now = timezone.now()
        current_hour = now.hour
        
        # 1. 24 soatdan kam qolgan deadline'lar
        deadline_24h = now + timedelta(hours=24)
        
        # 24 soat ichida tugaydigan bosqichlar
        steps_24h = ApprovalStep.objects.filter(
            status='pending',
            deadline__gt=now,  # Hali tugamagan
            deadline__lte=deadline_24h,  # 24 soatdan kam qolgan
            document__status='pending_approval',
            step_order=F('document__current_step'),
            approver__isnull=False
        ).select_related('document', 'approver')
        
        # 2. 2 soatdan kam qolgan deadline'lar
        deadline_2h = now + timedelta(hours=2)
        
        steps_2h = ApprovalStep.objects.filter(
            status='pending',
            deadline__gt=now,  # Hali tugamagan
            deadline__lte=deadline_2h,  # 2 soatdan kam qolgan
            document__status='pending_approval',
            step_order=F('document__current_step'),
            approver__isnull=False
        ).select_related('document', 'approver')
        
        notified_24h = 0
        notified_2h = 0
        
        # 24 soat qolgan bosqichlar uchun (batch)
        steps_24h_by_user = {}
        for step in steps_24h:
            steps_24h_by_user.setdefault(step.approver_id, []).append(step)

        for approver_id, steps in steps_24h_by_user.items():
            try:
                approver = steps[0].approver
                last_notification = models.Notification.objects.filter(
                    recipient=approver,
                    notification_type='deadline_24h'
                ).order_by('-created_at').first()

                should_notify = True
                if last_notification:
                    hours_since_last = (now - last_notification.created_at).total_seconds() / 3600
                    if hours_since_last < 12:
                        should_notify = False

                if should_notify:
                    remaining_hours = (steps[0].deadline - now).seconds // 3600
                    NotificationService.notify_deadline_batch(
                        approver=approver,
                        documents=[step.document for step in steps],
                        remaining_hours=remaining_hours,
                        is_urgent=False,
                        notification_type='deadline_24h'
                    )
                    notified_24h += 1
            except Exception as e:
                print(f"24H NOTIFICATION ERROR: {e}")
        
        # 2 soat qolgan bosqichlar uchun (batch)
        steps_2h_by_user = {}
        for step in steps_2h:
            steps_2h_by_user.setdefault(step.approver_id, []).append(step)

        for approver_id, steps in steps_2h_by_user.items():
            try:
                approver = steps[0].approver
                current_hour = now.hour
                night_start, night_end = ApprovalWorkflowService.NIGHT_HOURS

                if night_start <= current_hour or current_hour < night_end:
                    early_hour = ApprovalWorkflowService.EARLY_NOTIFY_HOUR
                    if current_hour >= early_hour:
                        continue

                last_notification = models.Notification.objects.filter(
                    recipient=approver,
                    notification_type='deadline_2h'
                ).order_by('-created_at').first()

                should_notify = True
                if last_notification:
                    hours_since_last = (now - last_notification.created_at).total_seconds() / 3600
                    if hours_since_last < 1:
                        should_notify = False

                if should_notify:
                    remaining_hours = (steps[0].deadline - now).seconds // 3600
                    remaining_minutes = ((steps[0].deadline - now).seconds % 3600) // 60

                    NotificationService.notify_deadline_batch(
                        approver=approver,
                        documents=[step.document for step in steps],
                        remaining_hours=remaining_hours,
                        remaining_minutes=remaining_minutes,
                        is_urgent=True,
                        notification_type='deadline_2h'
                    )

                    for step in steps:
                        NotificationService.notify_author_about_urgent_deadline(
                            document=step.document,
                            remaining_hours=remaining_hours,
                            remaining_minutes=remaining_minutes
                        )

                    notified_2h += 1
            except Exception as e:
                print(f"2H NOTIFICATION ERROR: {e}")
        
        return {
            'status': 'notified',
            'notified_24h': notified_24h,
            'notified_2h': notified_2h,
            'timestamp': now
        }
    
    @staticmethod
    def create_approval_steps(document, workflow_type='department_head'):
        """
        Hujjat uchun tasdiqlash bosqichlarini yaratish.
        Har bir bosqich uchun deadline 2 kun (48 soat) o'rnatiladi.
        """
        from datetime import timedelta
        from django.utils import timezone
        
        now = timezone.now()
        
        # Bosqichlarni yaratish
        steps = []
        
        if workflow_type == 'department_head':
            # 1. Kafedra mudiri
            # 2. Fakultet dekani
            roles = ['department_head', 'faculty_dean']
        elif workflow_type == 'teacher_only':
            # Faqat kafedra mudiri
            roles = ['department_head']
        elif workflow_type == 'full':
            # To'liq: Kafedra → Fakultet → Rektorat
            roles = ['department_head', 'faculty_dean', 'director']
        else:
            roles = ['department_head']
        
        for i, role in enumerate(roles):
            # Har bir bosqich uchun approver'ni topish
            approver = ApprovalWorkflowService._find_approver_for_role(
                document=document,
                role=role
            )
            
            # Deadline: hozirgi vaqt + 2 kun
            deadline = now + timedelta(
                hours=ApprovalWorkflowService.DEFAULT_APPROVAL_DEADLINE_HOURS
            )
            
            step = models.ApprovalStep.objects.create(
                document=document,
                step_order=i,
                role_required=role,
                approver=approver,
                deadline=deadline,
                status='pending'
            )
            
            steps.append(step)
            
            # Birinchi bosqich uchun darhol xabar
            if i == 0 and approver:
                NotificationService.notify_approval_needed(
                    document=document,
                    approver=approver
                )
        
        # Hujjatning current_step ni 0 ga o'rnatish
        document.current_step = 0
        document.save()
        
        return steps
    
    @staticmethod
    def _find_approver_for_role(document, role):
        """
        Berilgan rol uchun tasdiqlovchini topish.
        """
        from .models import User
        
        if role == 'department_head':
            # Kafedra mudirini topish
            if document.uploaded_by.department:
                return User.objects.filter(
                    active_role__role_type='department_head',
                    managed_department=document.uploaded_by.department
                ).first()
        
        elif role == 'faculty_dean':
            # Fakultet dekanini topish
            if document.uploaded_by.faculty:
                return User.objects.filter(
                    active_role__role_type='faculty_dean',
                    managed_faculty=document.uploaded_by.faculty
                ).first()
        
        elif role == 'director':
            # Rektor/direktorni topish
            return User.objects.filter(
                active_role__role_type='director'
            ).first()
        
        return None



class DocumentFilterService:
    """Hujjatlarni filtrlash va qidirish uchun xizmat"""

    @staticmethod
    def get_filtered_documents(user, filters: dict):
        """
        Foydalanuvchi roli va filterlar asosida hujjatlar ro'yxatini qaytaradi.
        """
        # 1. Asosiy so'rovnomani foydalanuvchi roliga qarab aniqlash
        if user.role in ['admin', 'director', 'director_deputy']:
            documents = models.Document.objects.all()
        elif user.role in ['faculty_dean', 'dean_deputy']:
            if hasattr(user, 'managed_faculty') and user.managed_faculty:
                documents = models.Document.objects.filter(uploaded_by__faculty=user.managed_faculty)
            elif user.faculty:
                documents = models.Document.objects.filter(uploaded_by__faculty=user.faculty)
            else:
                # Agar dekan fakultetga biriktirilmagan bo'lsa, faqat o'zinikini ko'radi
                documents = models.Document.objects.filter(uploaded_by=user)
        elif user.role == 'department_head':
            if hasattr(user, 'managed_department') and user.managed_department:
                documents = models.Document.objects.filter(uploaded_by__department=user.managed_department)
            elif user.department:
                documents = models.Document.objects.filter(uploaded_by__department=user.department)
            else:
                # Agar mudir kafedraga biriktirilmagan bo'lsa, faqat o'zinikini ko'radi
                documents = models.Document.objects.filter(uploaded_by=user)
        else:
            # Oddiy foydalanuvchilar (student, teacher) faqat o'zi yuklagan hujjatlarni ko'radi
            documents = models.Document.objects.filter(uploaded_by=user)

        # 2. Qo'shimcha filterlarni qo'llash
        status = filters.get('status')
        doc_type = filters.get('document_type')
        program = filters.get('program')
        subject = filters.get('subject')
        year = filters.get('academic_year')
        author = filters.get('author')
        department = filters.get('department')
        faculty = filters.get('faculty')
        university = filters.get('university')

        if status:
            documents = documents.filter(status=status)
        if doc_type:
            documents = documents.filter(document_type_id=doc_type)
        if program:
            documents = documents.filter(related_group__program_id=program)
        if subject:
            documents = documents.filter(subject_id=subject)
        if year:
            documents = documents.filter(academic_year_id=year)

        # Muallif bo'yicha qidiruv (faqat ruxsati borlarga, bu view qatlamida tekshiriladi)
        if author:
            documents = documents.filter(
                Q(uploaded_by__first_name__icontains=author) |
                Q(uploaded_by__last_name__icontains=author) |
                Q(uploaded_by__username__icontains=author)
            )

        # Tashkiliy tuzilma bo'yicha filterlar (faqat ruxsati borlarga, bu view qatlamida tekshiriladi)
        if department:
            documents = documents.filter(uploaded_by__department_id=department)
        if faculty:
            documents = documents.filter(uploaded_by__faculty_id=faculty)
        if university:
            documents = documents.filter(uploaded_by__university_id=university)

        return documents.order_by('-uploaded_at')
