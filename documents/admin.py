from django.contrib import admin
from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    User, Role, University, Faculty, Department, Program, Group,
    Subject, TeachingAllocation, AcademicYear, AuditLog, JobRun,
    DocumentType, Hujjat, ApprovalStep, ApprovalLog, Notification, RequestLog, SecurityPolicy
)
from import_export import resources, fields
from import_export.admin import ImportMixin
from import_export.widgets import ForeignKeyWidget

# ==================== ROLE ADMIN ====================
from import_export.widgets import Widget
from django.contrib.auth.hashers import make_password
import json

class RoleCodesWidget(Widget):
    def clean(self, value, row=None, **kwargs):
        if value in (None, ''):
            return ''
        if isinstance(value, (list, tuple)):
            return ",".join([str(v).strip() for v in value if str(v).strip()])
        text = str(value).strip()
        if text.startswith('['):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return ",".join([str(v).strip() for v in parsed if str(v).strip()])
            except Exception:
                return ''
        return text

    def render(self, value, obj=None):
        if value is None:
            return ""
        return str(value)

class PasswordWidget(Widget):
    def clean(self, value, row=None, **kwargs):
        if value in (None, ''):
            return None
        return make_password(str(value).strip())

    def render(self, value, obj=None):
        return ""

class OptionalPasswordField(fields.Field):
    def save(self, obj, data, is_m2m=False):
        if data in (None, ''):
            return
        super().save(obj, data, is_m2m)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin for Role model"""
    list_display = [
        'name', 
        'code', 
        'get_role_type_display', 
        'description_short',
        'is_active', 
        'is_default', 
        'created_at'
    ]
    list_filter = [
        'role_type', 
        'is_active', 
        'is_default', 
        'created_at'
    ]
    search_fields = ['name', 'code', 'description']
    list_editable = ['is_active', 'is_default']
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('role_type', 'name', 'code', 'description')
        }),
        ('Holat', {
            'fields': ('is_active', 'is_default')
        }),
    )
    
    def description_short(self, obj):
        """Qisqartirilgan tavsif"""
        if obj.description and len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description or "-"
    description_short.short_description = "Tavsif"
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('role_type', 'name')

# ==================== USER RESOURCE ====================
# ==================== USER RESOURCE (yangilash) ====================

class UserResource(resources.ModelResource):
    DEFAULT_PASSWORD = "12345678"

    password = OptionalPasswordField(
        column_name='password',
        attribute='password',
        widget=PasswordWidget()
    )
    university = fields.Field(
        column_name='universitet',
        attribute='university',
        widget=ForeignKeyWidget(University, 'name')
    )
    faculty = fields.Field(
        column_name='faculty',
        attribute='faculty',
        widget=ForeignKeyWidget(Faculty, 'name')
    )
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )
    program = fields.Field(
        column_name='program',
        attribute='program',
        widget=ForeignKeyWidget(Program, 'name')
    )
    group = fields.Field(
        column_name='group',
        attribute='group',
        widget=ForeignKeyWidget(Group, 'name')
    )
    # Rollar uchun text field
    roles_data = fields.Field(
        column_name='roles_data',
        attribute='roles_data',
        widget=RoleCodesWidget()
    )

    class Meta:
        model = User
        import_id_fields = ('username',)
        fields = ('username', 'first_name', 'last_name', 'middle_name', 'email',
                  'password', 'roles_data', 'university', 'faculty',
                  'department', 'program', 'group')
        skip_unchanged = True
        report_skipped = True

    def after_import_instance(self, instance, new, **kwargs):
        if not new:
            return
        if kwargs.get('dry_run'):
            return
        if not instance.has_usable_password():
            instance.set_password(self.DEFAULT_PASSWORD)
            instance.save(update_fields=['password'])


class SubjectResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'code')
    )

    class Meta:
        model = Subject
        import_id_fields = ('code', 'department')
        fields = (
            'name',
            'code',
            'credits',
            'lecture_hours',
            'practice_hours',
            'taught_in_programs',
            'department',
            'is_active',
        )
        skip_unchanged = True
        report_skipped = True


class TeachingAllocationResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'code')
    )
    teacher = fields.Field(
        column_name='teacher',
        attribute='teacher',
        widget=ForeignKeyWidget(User, 'username')
    )
    subject = fields.Field(
        column_name='subject',
        attribute='subject',
        widget=ForeignKeyWidget(Subject, 'code')
    )
    group = fields.Field(
        column_name='group',
        attribute='group',
        widget=ForeignKeyWidget(Group, 'name')
    )
    academic_year = fields.Field(
        column_name='academic_year',
        attribute='academic_year',
        widget=ForeignKeyWidget(AcademicYear, 'name')
    )

    class Meta:
        model = TeachingAllocation
        import_id_fields = ('subject', 'group', 'academic_year', 'semester')
        fields = (
            'department',
            'teacher',
            'subject',
            'group',
            'academic_year',
            'semester',
        )
        skip_unchanged = True
        report_skipped = True


# ==================== USER ADMIN (asosiy o'zgartirishlar) ====================

@admin.register(User)
class UserAdmin(ImportMixin, BaseUserAdmin):
    """Admin for User model with Excel import"""
    resource_class = UserResource
    
    list_display = [
        'username', 
        'email', 
        'get_full_name', 
        'get_active_role_display',
        'get_roles_count',
        'get_role_types_preview',
        'faculty', 
        'department', 
        'is_active'
    ]
    list_filter = [
        'active_role__role_type', 
        'faculty', 
        'department', 
        'is_active', 
        'is_staff'
    ]
    search_fields = [
        'username', 
        'email', 
        'first_name', 
        'last_name',
        'middle_name',
        'active_role__name',
        'active_role__code'
    ]
    
    # ManyToMany maydonlari yo'q, shuning uchun filter_horizontal kerak emas
    # filter_horizontal = []
    
    # Fieldsets ni yangilash
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Shaxsiy ma\'lumotlar', {
            'fields': ('middle_name',)
        }),
        ('Rollar', {
            'fields': ('roles_data', 'active_role'),
            'description': '''
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>Rollar kodlari (vergul bilan):</strong> <br>
                <code>TEACHER_BASIC,DEPARTMENT_HEAD_BASIC</code><br>
                <small>Bir nechta rol qo'shish mumkin.</small>
            </div>
            '''
        }),
        ('Tashkiliy tuzilma', {
            'fields': ('university', 'faculty', 'department', 'program', 'group',
                      'managed_department', 'managed_faculty')
        }),
        ('Bildirishnomalar', {
            'fields': ('email_notifications', 'push_notifications')
        }),
    )
    
   
    # Yangi metodlar
    def get_active_role_display(self, obj):
        """Faol rol nomini ko'rsatish"""
        return obj.get_active_role_display()
    get_active_role_display.short_description = "Faol rol"
    
    def get_roles_count(self, obj):
        """Rollar sonini ko'rsatish"""
        return len(obj.get_role_objects())
    get_roles_count.short_description = "Rollar soni"
    
    def get_role_types_preview(self, obj):
        """Rol tiplarini qisqacha ko'rsatish"""
        role_types = obj.get_role_types()
        if role_types:
            # Rol tiplarini o'zbek tilida ko'rsatish
            role_type_names = {
                'student': 'Talaba',
                'teacher': "O'qituvchi",
                'department_head': 'Kafedra mudiri',
                'faculty_dean': 'Fakultet dekani',
                'dean_deputy': 'Dekan o\'rinbosari',
                'academic_office': 'O\'quv bo\'limi',
                'registration_office': 'Registratura',
                'director': 'Direktor',
                'director_deputy': 'Direktor o\'rinbosari',
            }
            
            display_names = [role_type_names.get(rt, rt) for rt in role_types[:2]]
            display = ', '.join(display_names)
            
            if len(role_types) > 2:
                display += f'... (+{len(role_types) - 2})'
            return display
        return "Rollar yo'q"
    get_role_types_preview.short_description = "Rollar"
    
    def get_full_name(self, obj):
        """To'liq ismni ko'rsatish"""
        return obj.get_full_name()
    get_full_name.short_description = "To'liq ism"
    
    # Oldingi metodni saqlab qolish (oldingi kod bilan moslashish)
    def get_role_display(self, obj):
        """Legacy metod (oldingi kod bilan moslashish)"""
        return obj.get_active_role_display()
    get_role_display.short_description = "Rol"
    
    def get_role_type(self, obj):
        """Legacy metod"""
        if obj.active_role:
            return obj.active_role.get_role_type_display()
        return "-"
    get_role_type.short_description = "Rol tipi"
    
    # JSON ni tozalash va validatsiya
    def save_model(self, request, obj, form, change):
        """Model saqlashda rollar kodlarini tozalash"""
        if isinstance(obj.roles_data, str):
            obj.roles_data = ",".join([code.strip() for code in obj.roles_data.split(',') if code.strip()])

        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'active_role', 'faculty', 'department', 'program', 'group'
        )
    
    # JSON Widget klassi
    class JSONWidget(forms.Textarea):
        def render(self, name, value, attrs=None, renderer=None):
            if isinstance(value, (list, dict)):
                import json
                value = json.dumps(value, indent=2, ensure_ascii=False)
            return super().render(name, value, attrs, renderer)

# ==================== ORGANIZATION ADMINS ====================

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'website', 'created_at']
    search_fields = ['name', 'code']


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'university', 'created_at']
    list_filter = ['university']
    search_fields = ['name', 'code']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('university')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'faculty', 'get_university', 'created_at']
    list_filter = ['faculty__university', 'faculty']
    search_fields = ['name', 'code']
    
    def get_university(self, obj):
        return obj.faculty.university.name
    get_university.short_description = 'University'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('faculty__university')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'degree_level', 'duration_years', 'created_at']
    list_filter = ['degree_level', 'department__faculty']
    search_fields = ['name', 'code']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department__faculty')

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'start_date']
    search_fields = ['name']

@admin.register(Subject)
class SubjectAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = SubjectResource
    list_display = ['name', 'code', 'department', 'credits', 'is_active', 'updated_at']
    list_filter = ['department', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'department__name']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department')


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'program', 'get_current_course', 'created_at']
    list_filter = ['program__department__faculty']
    search_fields = ['name', 'program__name']
    
    def get_current_course(self, obj):
        return obj.current_course
    get_current_course.short_description = 'Current Course'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('program__department__faculty')

@admin.register(TeachingAllocation)
class TeachingAllocationAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = TeachingAllocationResource
    list_display = [
        'teacher',
        'subject',
        'group',
        'academic_year',
        'semester',
        'department',
        'created_at',
    ]
    list_filter = [
        'academic_year',
        'semester',
        'department',
        'created_at',
    ]
    search_fields = [
        'teacher__first_name',
        'teacher__last_name',
        'teacher__username',
        'subject__name',
        'group__name',
    ]
    autocomplete_fields = ['teacher', 'subject', 'group', 'academic_year', 'department']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'teacher', 'subject', 'group', 'academic_year', 'department'
        )


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at',
        'method',
        'path',
        'status_code',
        'user',
        'ip_address',
        'duration_ms',
    ]
    list_filter = [
        'method',
        'status_code',
        'created_at',
    ]
    search_fields = [
        'path',
        'query_string',
        'user__username',
        'ip_address',
    ]
    readonly_fields = [
        'created_at',
        'user',
        'method',
        'path',
        'query_string',
        'status_code',
        'ip_address',
        'user_agent',
        'referrer',
        'duration_ms',
        'request_body',
        'request_bytes',
        'response_bytes',
    ]


@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'rate_limit_per_minute',
        'burst',
        'findtime_seconds',
        'maxretry',
        'bantime_seconds',
        'updated_at',
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Limits', {
            'fields': (
                'rate_limit_per_minute',
                'burst',
                'findtime_seconds',
                'maxretry',
                'bantime_seconds',
            )
        }),
        ('Whitelist', {
            'fields': ('whitelist',),
            'description': 'IP yoki CIDR qiymatlarini vergul yoki yangi qatorda kiriting.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

# ==================== DOCUMENT TYPE ADMIN ====================

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'max_file_size_mb', 
        'deadline_hours', 
        'get_workflow', 
        'get_allowed_roles_count',
        'get_requirements',
        'is_active', 
        'created_at'
    ]
    list_filter = [
        'is_active', 
        'requires_subject', 
        'requires_academic_year', 
        'requires_group', 
        'created_at'
    ]
    search_fields = ['name', 'description']
    
   
    
    fieldsets = (
        ('Asosiy informatsiyalar', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Fayl sozlamalari', {
            'fields': ('max_file_size_mb', 'allowed_extensions')
        }),
        ('Tasdiqlash ketma-ketligi', {
            'fields': ('approval_workflow', 'deadline_hours'),
            'description': 'Define the sequence of roles that must approve this document type'
        }),
        ('Hujjat talablari', {
            'fields': ('requires_subject', 'requires_academic_year', 'requires_group'),
            'description': 'Hujjat yuklashda qaysi ma\'lumotlar majburiy ekanligini belgilang'
        }),
        ('Ruxsat etilgan rollar', {
            'fields': ('allowed_roles',),
            'description': 'Bu turdagi hujjat yuklashi mumkin bo\'lgan rollar. Bo\'sh qoldirilsa, hamma yuklashi mumkin.'
        }),
    )
    
    def get_workflow(self, obj):
        return obj.get_workflow_display()
    get_workflow.short_description = 'Tasdiqlash ketma-ketligi'
    
    def get_allowed_roles_count(self, obj):
        count = len(obj.allowed_roles or [])
        if count == 0:
            return "Hamma"
        return f"{count} ta"
    get_allowed_roles_count.short_description = 'Ruxsat etilgan rollar'
    
    def get_requirements(self, obj):
        """Majburiy maydonlarni ko'rsatish"""
        requirements = []
        if obj.requires_subject:
            requirements.append('Fan')
        if obj.requires_academic_year:
            requirements.append('O\'quv yili')
        if obj.requires_group:
            requirements.append('Guruh')
        
        return ', '.join(requirements) if requirements else 'Hech qanday'
    get_requirements.short_description = 'Majburiy maydonlar'
    
    def get_queryset(self, request):
        return super().get_queryset(request)

# ==================== DOCUMENT ADMINS ====================

class ApprovalStepInline(admin.TabularInline):
    model = ApprovalStep
    extra = 0
    readonly_fields = ['step_order', 'role_required', 'approver', 'status', 'deadline', 'approved_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class ApprovalLogInline(admin.TabularInline):
    model = ApprovalLog
    extra = 0
    readonly_fields = ['approval_step', 'approver', 'action', 'comment', 'timestamp', 'ip_address']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False






# ==================== DOCUMENT ADMINS ====================

@admin.register(Hujjat)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'file_name', 
        'document_type', 
        'uploaded_by', 
        'get_department',
        'get_roles_of_uploader',  # Yangi
        'get_active_role_of_uploader',
        'status', 
        'current_step',
        'uploaded_at',
        'view_link'
    ]
    list_filter = [
        'status', 
        'document_type', 
        'uploaded_by__faculty',
        'uploaded_by__department',
        'uploaded_at'
    ]
    search_fields = [
        'file_name', 
        'uploaded_by__username', 
        'uploaded_by__first_name', 
        'uploaded_by__last_name',
        'verification_code'
    ]
    readonly_fields = [
        'uuid', 
        'verification_code', 
        'uploaded_at', 
        'updated_at', 
        'completed_at',
        'file_size',
        'get_expected_approver'
    ]
    
    fieldsets = (
        ('Hujjat Information', {
            'fields': ('document_type', 'uploaded_by', 'file', 'file_name', 'file_size', 'title', 'description')
        }),
        ('Status', {
            'fields': ('status', 'current_step', 'get_expected_approver')
        }),
        ('Verification', {
            'fields': ('uuid', 'verification_code', 'qr_code_image', 'final_pdf')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'updated_at', 'completed_at')
        }),
    )
    
    inlines = [ApprovalStepInline, ApprovalLogInline]
    
    def get_department(self, obj):
        if obj.uploaded_by and obj.uploaded_by.department:
            return obj.uploaded_by.department.name
        return '-'
    get_department.short_description = 'Kafedra'
    
    # Eski metodni almashtirish
    def get_active_role_of_uploader(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_active_role_display()
        return '-'
    get_active_role_of_uploader.short_description = 'Faol rol'
    
    # Yangi metod
    def get_roles_of_uploader(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_roles_display()
        return '-'
    get_roles_of_uploader.short_description = 'Barcha rollar'
    
    def get_expected_approver(self, obj):
        return obj.get_expected_approver_text()
    get_expected_approver.short_description = 'Joriy holat'
    
    def view_link(self, obj):
        url = reverse('documents:document_detail', args=[obj.id])
        return format_html('<a href="{}" target="_blank" class="button">Ko\'rish</a>', url)
    view_link.short_description = 'Harakatlar'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'document_type', 
            'uploaded_by__faculty',
            'uploaded_by__department'
            # uploaded_by__role kerak emas endi
        )






@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = [
        'document', 
        'step_order', 
        'role_required', 
        'get_approver_name', 
        'status', 
        'deadline', 
        'is_overdue'
    ]
    list_filter = ['status', 'role_required', 'deadline']
    search_fields = ['document__file_name', 'approver__username', 'role_required']
    readonly_fields = ['document', 'step_order', 'role_required', 'deadline', 'approved_at']
    
    def get_approver_name(self, obj):
        if obj.approver:
            return obj.approver.get_full_name()
        return "Tayinlanmagan"
    get_approver_name.short_description = "Tasdiqlovchi"
    
    def is_overdue(self, obj):
        return obj.is_overdue()
    is_overdue.boolean = True
    is_overdue.short_description = "Muddati o'tgan"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('document', 'approver')





@admin.register(ApprovalLog)
class ApprovalLogAdmin(admin.ModelAdmin):
    list_display = [
        'document', 
        'get_approver_name', 
        'get_approver_roles',  # Yangi
        'action', 
        'get_role_of_approver', 
        'timestamp', 
        'ip_address'
    ]
    list_filter = ['action', 'timestamp']
    search_fields = ['document__file_name', 'approver__username', 'comment']
    readonly_fields = ['document', 'approval_step', 'approver', 'action', 'comment', 'timestamp', 'ip_address', 'user_agent']
    
    def get_approver_name(self, obj):
        if obj.approver:
            return obj.approver.get_full_name()
        return "-"
    get_approver_name.short_description = "Tasdiqlovchi"
    
    # Eski metod (oldingi kod bilan moslashish)
    def get_role_of_approver(self, obj):
        if obj.approver:
            return obj.approver.get_active_role_display()
        return "-"
    get_role_of_approver.short_description = "Faol rol"
    
    # Yangi metod
    def get_approver_roles(self, obj):
        if obj.approver:
            return obj.approver.get_roles_display()
        return "-"
    get_approver_roles.short_description = "Barcha rollar"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('document', 'approval_step', 'approver')


# ==================== CUSTOM ACTIONS (qo'shimcha) ====================

@admin.action(description="Rolni barcha foydalanuvchilarga qo'shish")
def add_role_to_all_users(modeladmin, request, queryset):
    """Tanlangan rolni barcha foydalanuvchilarga qo'shish"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    for role in queryset:
        users = User.objects.all()
        for user in users:
            if not user.has_role(role.code):
                user.add_role(role)
        
        modeladmin.message_user(
            request,
            f"'{role.name}' roli {users.count()} ta foydalanuvchiga qo'shildi",
            messages.SUCCESS
        )

@admin.action(description="Rolni barcha foydalanuvchilardan olib tashlash")
def remove_role_from_all_users(modeladmin, request, queryset):
    """Tanlangan rolni barcha foydalanuvchilardan olib tashlash"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    for role in queryset:
        users = User.objects.all()
        for user in users:
            if user.has_role(role.code):
                user.remove_role(role.code)
        
        modeladmin.message_user(
            request,
            f"'{role.name}' roli {users.count()} ta foydalanuvchidan olib tashlandi",
            messages.SUCCESS
        )



@admin.action(description="Foydalanuvchiga rol qo'shish")
def add_role_to_selected_users(modeladmin, request, queryset):
    """Tanlangan foydalanuvchilarga rol qo'shish"""
    from django.shortcuts import redirect
    from django.urls import reverse
    
    user_ids = queryset.values_list('id', flat=True)
    
    # Rol tanlash sahifasiga yo'naltirish
    return redirect(
        reverse('admin:add_role_to_users') + 
        f'?user_ids={",".join(map(str, user_ids))}'
    )

@admin.action(description="Foydalanuvchidan rol olib tashlash")
def remove_role_from_selected_users(modeladmin, request, queryset):
    """Tanlangan foydalanuvchilardan rol olib tashlash"""
    from django.shortcuts import redirect
    from django.urls import reverse
    
    user_ids = queryset.values_list('id', flat=True)
    
    # Rol olib tashlash sahifasiga yo'naltirish
    return redirect(
        reverse('admin:remove_role_from_users') + 
        f'?user_ids={",".join(map(str, user_ids))}'
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'recipient', 
        'notification_type', 
        'title_short', 
        'is_read', 
        'sent_email', 
        'sent_push', 
        'created_at'
    ]
    list_filter = ['notification_type', 'is_read', 'sent_email', 'sent_push', 'created_at']
    search_fields = ['recipient__username', 'title', 'message']
    readonly_fields = ['recipient', 'notification_type', 'title', 'message', 'document', 'created_at']
    
    def title_short(self, obj):
        """Qisqartirilgan sarlavha"""
        if obj.title and len(obj.title) > 50:
            return f"{obj.title[:50]}..."
        return obj.title
    title_short.short_description = "Sarlavha"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'document')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'document', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'document__file_name']
    readonly_fields = ['user', 'action', 'document', 'metadata', 'ip_address', 'user_agent', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'last_status', 'last_run_at', 'last_success_at', 'last_duration_ms']
    list_filter = ['last_status']
    search_fields = ['task_name']
    readonly_fields = [
        'task_name',
        'last_status',
        'last_run_at',
        'last_success_at',
        'last_error',
        'last_duration_ms',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

# ==================== CUSTOM ACTIONS ====================

@admin.action(description="Tanlangan rollarni faollashtirish")
def activate_roles(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description="Tanlangan rollarni faolsizlashtirish")
def deactivate_roles(modeladmin, request, queryset):
    queryset.update(is_active=False)

@admin.action(description="Tanlangan rollarni standart qilish")
def make_default_roles(modeladmin, request, queryset):
    # Avval barcha rollarni standart emas qilish
    for role in queryset:
        Role.objects.filter(role_type=role.role_type).update(is_default=False)
    # Keyin tanlanganlarni standart qilish
    queryset.update(is_default=True)

# Role admin uchun action'larni qo'shish
RoleAdmin.actions = [activate_roles, deactivate_roles, make_default_roles]

# User admin uchun action'lar
@admin.action(description="Tanlangan foydalanuvchilarni faollashtirish")
def activate_users(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description="Tanlangan foydalanuvchilarni faolsizlashtirish")
def deactivate_users(modeladmin, request, queryset):
    queryset.update(is_active=False)

UserAdmin.actions = [activate_users, deactivate_users]

# DocumentType admin uchun action'lar
@admin.action(description="Tanlangan hujjat turlarini faollashtirish")
def activate_document_types(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description="Tanlangan hujjat turlarini faolsizlashtirish")
def deactivate_document_types(modeladmin, request, queryset):
    queryset.update(is_active=False)

DocumentTypeAdmin.actions = [activate_document_types, deactivate_document_types]





# admin.py oxiriga qo'shing

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import Role

@staff_member_required
def add_role_to_users_view(request):
    """Foydalanuvchilarga rol qo'shish sahifasi"""
    user_ids = request.GET.get('user_ids', '').split(',')
    
    if request.method == 'POST':
        role_id = request.POST.get('role_id')
        role = Role.objects.get(id=role_id)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        users = User.objects.filter(id__in=user_ids)
        count = 0
        for user in users:
            if user.add_role(role):
                count += 1
        
        messages.success(request, f"{count} ta foydalanuvchiga '{role.name}' roli qo'shildi")
        return redirect('admin:auth_user_changelist')
    
    roles = Role.objects.filter(is_active=True)
    return render(request, 'admin/add_role_to_users.html', {
        'user_ids': user_ids,
        'roles': roles,
    })
