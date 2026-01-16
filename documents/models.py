

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator
from django.utils import timezone
from datetime import timedelta
import uuid
import random
import string
import json

# ==================== ROLE MODELI ====================

class Role(models.Model):
    """
    Tizimdagi rollar modeli.
    Har bir rol ROLE_CHOICES dagi rollardan biriga mos keladi.
    """
    # Asosiy rol tanlovlari (User modelidagi ROLE_CHOICES bilan bir xil)
    ROLE_TYPE_CHOICES = [
        ('student', 'Talaba'),
        ('teacher', "O'qituvchi"),
        ('department_head', 'Kafedra mudiri'),
        ('faculty_dean', 'Fakultet dekani'),
        ('dean_deputy', 'Dekan o\'rinbosari'),
        ('academic_office', 'O\'quv bo\'limi'),
        ('registration_office', 'Registratura'),
        ('director', 'Direktor'),
        ('director_deputy', 'Direktor o\'rinbosari'),
    ]
    
    # Rol tipi - ROLE_CHOICES dan biriga mos keladi
    role_type = models.CharField(
        max_length=30,
        choices=ROLE_TYPE_CHOICES,
        verbose_name="Rol tipi",
        help_text="Bu rol qaysi asosiy tizim roliga mos keladi"
    )
    
    # Rolning nomi (masalan: "Katta o'qituvchi", "Bosh metodist" va h.k.)
    name = models.CharField(max_length=100, verbose_name="Rol nomi")
    
    # Rol kodi (ichki identifikator)
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Rol kodi",
        help_text="Ichki identifikator (masalan: SENIOR_TEACHER)"
    )
    
    # Rol tavsifi
    description = models.TextField(blank=True, verbose_name="Tavsif")
    
    # Faollik holati
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    is_default = models.BooleanField(default=False, verbose_name="Standart rol")
    
    # Vaqt belgilari
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")
    
    class Meta:
        db_table = 'roles'
        verbose_name = "Rol"
        verbose_name_plural = "Rollar"
        ordering = ['role_type', 'name']
        indexes = [
            models.Index(fields=['role_type', 'is_active']),
            models.Index(fields=['code']),
        ]
        # Bir xil role_type va code kombinatsiyasi takrorlanmasligi kerak
        unique_together = [['role_type', 'code']]
    
    def __str__(self):
        return f"{self.name} ({self.get_role_type_display()})"
    
    def save(self, *args, **kwargs):
        # Agar standart rol bo'lsa, kodni avtomatik yaratish
        if not self.code:
            self.code = f"{self.role_type.upper()}_{self.name.upper().replace(' ', '_').replace('-', '_')}"
        
        # Agar is_default True bo'lsa, boshqa default rollarni False qilish
        if self.is_default and self.role_type:
            Role.objects.filter(role_type=self.role_type, is_default=True).exclude(id=self.id).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_default_role_for_type(cls, role_type):
        """Berilgan rol tipi uchun standart rolni olish"""
        try:
            return cls.objects.get(role_type=role_type, is_default=True, is_active=True)
        except cls.DoesNotExist:
            # Agar standart rol topilmasa, birinchi faol rolni qaytarish
            return cls.objects.filter(role_type=role_type, is_active=True).first()
    
    @classmethod
    def get_role_by_code(cls, code):
        """Kod bo'yicha rolni olish"""
        try:
            return cls.objects.get(code=code, is_active=True)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_roles_by_type(cls, role_type):
        """Rol tipi bo'yicha rollarni olish"""
        return cls.objects.filter(role_type=role_type, is_active=True).order_by('name')
    
    @classmethod
    def initialize_default_roles(cls):
        """Standart rollarni yaratish/yuklash"""
        default_roles = [
            # Talaba rollari
            {
                'role_type': 'student',
                'name': 'Talaba',
                'code': 'STUDENT_BASIC',
                'description': 'Asosiy talaba roli',
                'is_default': True,
            },
            
            # O'qituvchi rollari
            {
                'role_type': 'teacher',
                'name': "O'qituvchi",
                'code': 'TEACHER_BASIC',
                'description': "Asosiy o'qituvchi roli",
                'is_default': True,
            },
            {
                'role_type': 'teacher',
                'name': 'Katta o\'qituvchi',
                'code': 'TEACHER_SENIOR',
                'description': 'Tajribali katta o\'qituvchi',
            },
            {
                'role_type': 'teacher',
                'name': 'Metodist',
                'code': 'TEACHER_METHODIST',
                'description': "O'quv-uslubiy materiallar uchun metodist",
            },
            
            # Kafedra mudirlari rollari
            {
                'role_type': 'department_head',
                'name': 'Kafedra mudiri',
                'code': 'DEPARTMENT_HEAD_BASIC',
                'description': 'Kafedra mudiri',
                'is_default': True,
            },
            {
                'role_type': 'department_head',
                'name': 'Kafedra mudiri o\'rinbosari',
                'code': 'DEPARTMENT_DEPUTY_HEAD',
                'description': 'Kafedra mudirining o\'rinbosari',
            },
            
            # Fakultet dekanlari rollari
            {
                'role_type': 'faculty_dean',
                'name': 'Fakultet dekani',
                'code': 'FACULTY_DEAN_BASIC',
                'description': 'Fakultet dekani',
                'is_default': True,
            },
            
            # Dekan o'rinbosarlari rollari
            {
                'role_type': 'dean_deputy',
                'name': 'Dekan o\'rinbosari',
                'code': 'DEAN_DEPUTY_BASIC',
                'description': 'Dekan o\'rinbosari',
                'is_default': True,
            },
            {
                'role_type': 'dean_deputy',
                'name': 'Dekan o\'rinbosari (o\'quv)',
                'code': 'DEAN_DEPUTY_ACADEMIC',
                'description': 'O\'quv ishlari bo\'yicha dekan o\'rinbosari',
            },
            {
                'role_type': 'dean_deputy',
                'name': 'Dekan o\'rinbosari (ilmiy)',
                'code': 'DEAN_DEPUTY_RESEARCH',
                'description': 'Ilmiy ishlar bo\'yicha dekan o\'rinbosari',
            },
            
            # O'quv bo'limi rollari
            {
                'role_type': 'academic_office',
                'name': 'O\'quv bo\'limi xodimi',
                'code': 'ACADEMIC_OFFICE_STAFF',
                'description': 'O\'quv bo\'limi xodimi',
                'is_default': True,
            },
            {
                'role_type': 'academic_office',
                'name': 'O\'quv bo\'limi boshlig\'i',
                'code': 'ACADEMIC_OFFICE_HEAD',
                'description': 'O\'quv bo\'limi boshlig\'i',
            },
            
            # Registratura rollari
            {
                'role_type': 'registration_office',
                'name': 'Registratura xodimi',
                'code': 'REGISTRATION_OFFICE_STAFF',
                'description': 'Registratura xodimi',
                'is_default': True,
            },
            {
                'role_type': 'registration_office',
                'name': 'Registratura boshlig\'i',
                'code': 'REGISTRATION_OFFICE_HEAD',
                'description': 'Registratura boshlig\'i',
            },
            
            # Direktor rollari
            {
                'role_type': 'director',
                'name': 'Direktor',
                'code': 'DIRECTOR_BASIC',
                'description': 'Universitet direktori',
                'is_default': True,
            },
            
            # Direktor o'rinbosarlari rollari
            {
                'role_type': 'director_deputy',
                'name': 'Direktor o\'rinbosari',
                'code': 'DIRECTOR_DEPUTY_BASIC',
                'description': 'Direktor o\'rinbosari',
                'is_default': True,
            },
            {
                'role_type': 'director_deputy',
                'name': 'Direktor o\'rinbosari (o\'quv)',
                'code': 'DIRECTOR_DEPUTY_ACADEMIC',
                'description': 'O\'quv ishlari bo\'yicha direktor o\'rinbosari',
            },
            {
                'role_type': 'director_deputy',
                'name': 'Direktor o\'rinbosari (ilmiy)',
                'code': 'DIRECTOR_DEPUTY_RESEARCH',
                'description': 'Ilmiy ishlar bo\'yicha direktor o\'rinbosari',
            },
            {
                'role_type': 'director_deputy',
                'name': 'Direktor o\'rinbosari (ma\'muriy)',
                'code': 'DIRECTOR_DEPUTY_ADMIN',
                'description': 'Ma\'muriy ishlar bo\'yicha direktor o\'rinbosari',
            },
        ]
        
        created_roles = []
        for role_data in default_roles:
            role, created = cls.objects.get_or_create(
                code=role_data['code'],
                defaults=role_data
            )
            if created:
                created_roles.append(role)
        
        return created_roles


class User(AbstractUser):
    """Extended user model with role and organizational assignment"""

    middle_name = models.CharField(max_length=150, blank=True) 

    roles_data = models.TextField(
        verbose_name="Rollar",
        help_text="Foydalanuvchi rollari kodlari vergul bilan ajratilgan",
        default="",
        blank=True,
    )
    active_role = models.ForeignKey(
        'Role', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='active_users'
    )

    email = models.EmailField(blank=True, null=True)
    hemis_id = models.CharField(max_length=50, blank=True, null=True, unique=True)

    # Organizational assignments
    university = models.ForeignKey('University', on_delete=models.SET_NULL, null=True, blank=True)
    faculty = models.ForeignKey('Faculty', on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    program = models.ForeignKey('Program', on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True)
    
    # For department heads and deans
    managed_department = models.OneToOneField('Department', on_delete=models.SET_NULL, 
                                              null=True, blank=True, related_name='head')
    managed_faculty = models.OneToOneField('Faculty', on_delete=models.SET_NULL, 
                                           null=True, blank=True, related_name='dean')
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['active_role', 'faculty', 'department']),
        ]
    
    @property
    def role(self):
        """Legacy code uchun - faol rol turini qaytarish"""
        return self.get_active_role_type()
    
    @property
    def role_name(self):
        """Rol nomi"""
        return self.get_active_role_display()

    def get_full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        full_name = " ".join(part for part in parts if part)
        return full_name.strip() or self.username

    def _get_role_codes(self):
        cached = getattr(self, "_role_codes_cache", None)
        if cached is not None:
            return cached
        if not self.roles_data:
            self._role_codes_cache = []
            return self._role_codes_cache
        if isinstance(self.roles_data, (list, tuple)):
            raw_roles = self.roles_data
        else:
            text = str(self.roles_data).strip()
            if not text:
                self._role_codes_cache = []
                return self._role_codes_cache
            if text.startswith('['):
                try:
                    raw_roles = json.loads(text)
                except Exception:
                    raw_roles = text.split(',')
            else:
                raw_roles = text.split(',')

        role_codes = []
        seen = set()
        for code in raw_roles:
            if isinstance(code, dict):
                code = code.get('code', '')
            code = str(code).strip()
            if code and code not in seen:
                role_codes.append(code)
                seen.add(code)
        self._role_codes_cache = role_codes
        return role_codes
    
    
    def add_role_by_code(self, role_code):
        """Rol kod bo'yicha qo'shish"""
        role = Role.get_role_by_code(role_code)
        if role:
            return self.add_role(role)
        return False

    def get_active_role_type(self):
        if self.is_superuser:
            return 'admin'
        if self.active_role:
            return self.active_role.role_type
        role_codes = self._get_role_codes()
        if role_codes:
            role_obj = Role.get_role_by_code(role_codes[0])
            if role_obj:
                return role_obj.role_type
        return None

    def is_active_role(self, role_type: str) -> bool:
        return self.get_active_role_type() == role_type

    
    def add_role(self, role_obj):
        """Role obyekti qo'shish"""
        if not self.has_role(role_obj.code):
            role_codes = self._get_role_codes()
            role_codes.append(role_obj.code)
            self.roles_data = ",".join(role_codes)

            if not self.active_role:
                self.active_role = role_obj

            self.save()
            return True
        return False
    
    def remove_role(self, role_code):
        """Rolni olib tashlash"""
        role_codes = self._get_role_codes()
        if role_code in role_codes:
            role_codes = [code for code in role_codes if code != role_code]
            self.roles_data = ",".join(role_codes)

            if self.active_role and self.active_role.code == role_code:
                self.active_role = None
                if role_codes:
                    self.active_role = Role.get_role_by_code(role_codes[0])

            self.save()
            return True
        return False
    
    def has_role(self, role_code):
        """Berilgan rol mavjudligini tekshirish"""
        if self.active_role and self.active_role.code == role_code:
            return True
        role_codes = self._get_role_codes()
        return role_code in role_codes
    
    def has_role_type(self, role_type):
        """Berilgan rol tipi mavjudligini tekshirish"""
        if self.active_role and self.active_role.role_type == role_type:
            return True
        role_codes = self._get_role_codes()
        for code in role_codes:
            role_obj = Role.get_role_by_code(code)
            if role_obj and role_obj.role_type == role_type:
                return True
        return False
    
    def get_active_roles(self):
        """Faol rollarni olish"""
        return self.get_role_objects()
    
    def get_role_objects(self):
        """Role obyektlarini olish"""
        cached = getattr(self, "_role_objects_cache", None)
        if cached is not None:
            return cached
        role_codes = self._get_role_codes()
        if not role_codes:
            self._role_objects_cache = []
            return self._role_objects_cache
        roles = Role.objects.filter(code__in=role_codes, is_active=True)
        role_map = {role.code: role for role in roles}
        self._role_objects_cache = [role_map[code] for code in role_codes if code in role_map]
        return self._role_objects_cache
    
    def get_role_types(self):
        """Rol tiplarini olish"""
        types = set()
        if self.active_role and self.active_role.role_type:
            types.add(self.active_role.role_type)
        for role_obj in self.get_role_objects():
            if role_obj.role_type:
                types.add(role_obj.role_type)
        return list(types)
    
    def get_role_names(self):
        """Rol nomlarini olish"""
        names = []
        if self.active_role and self.active_role.name:
            names.append(self.active_role.name)
        for role_obj in self.get_role_objects():
            if role_obj.name and role_obj.name not in names:
                names.append(role_obj.name)
        return names
    
    def get_roles_display(self):
        """Rollarni ko'rsatish uchun formatlangan"""
        names = self.get_role_names()
        if names:
            return ", ".join(names)
        return "Rollar aniqlanmagan"
    
    def update_role_data(self, role_obj):
        """Text roles_data ishlatilganda maxsus yangilash talab qilinmaydi"""
        return False
    
    # ==================== SPECIFIC ROLE PROPERTIES ====================
    
    @property
    def is_department_head(self):
        """Kafedra mudiri ekanligini tekshirish"""
        return self.has_role_type('department_head') and self.managed_department is not None
    
    @property
    def is_faculty_dean(self):
        """Fakultet dekani ekanligini tekshirish"""
        return self.has_role_type('faculty_dean') and self.managed_faculty is not None
    
    @property
    def is_teacher(self):
        """O'qituvchi ekanligini tekshirish"""
        return self.has_role_type('teacher')
    
    @property
    def is_student(self):
        """Talaba ekanligini tekshirish"""
        return self.has_role_type('student')
    
    @property
    def is_director(self):
        """Direktor ekanligini tekshirish"""
        return self.has_role_type('director')
    
    @property
    def is_director_deputy(self):
        """Direktor o'rinbosari ekanligini tekshirish"""
        return self.has_role_type('director_deputy')
    
    @property
    def is_academic_office(self):
        """O'quv bo'limi xodimi ekanligini tekshirish"""
        return self.has_role_type('academic_office')
    
    @property
    def is_registration_office(self):
        """Registratura xodimi ekanligini tekshirish"""
        return self.has_role_type('registration_office')
    
    @property
    def is_dean_deputy(self):
        """Dekan o'rinbosari ekanligini tekshirish"""
        return self.has_role_type('dean_deputy')
    
    # ==================== MULTI-ROLE PERMISSIONS ====================
    
    def get_highest_role(self):
        """Eng yuqori rolni aniqlash (hierarxiya bo'yicha)"""
        role_hierarchy = [
            'director',
            'director_deputy', 
            'faculty_dean',
            'dean_deputy',
            'department_head',
            'teacher',
            'academic_office',
            'registration_office',
            'student'
        ]
        
        user_role_types = self.get_role_types()
        for role_type in role_hierarchy:
            if role_type in user_role_types:
                return role_type
        return None
    
    def can_upload_document_type(self, document_type):
        """Hujjat turini yuklasha oladimi?"""
        # Agar allowed_roles bo'sh bo'lsa, hamma yuklashi mumkin
        if not document_type.allowed_roles:
            return True
        
        # Foydalanuvchining har qanday roli ruxsat etilgan ro'yxatda bormi?
        user_role_types = self.get_role_types()
        for role_type in user_role_types:
            if role_type in document_type.allowed_roles:
                return True
        return False
    
    def can_view_document(self, document):
        """Hujjatni ko'risha oladimi?"""
        # O'zi yuklagan hujjatni ko'rishi mumkin
        if document.uploaded_by == self:
            return True
        
        # Direktor va direktor o'rinbosarlari hamma hujjatni ko'ra oladi
        if self.has_role_type('director') or self.has_role_type('director_deputy'):
            return True
        
        # Fakultet dekani va o'rinbosarlari o'z fakultetidagi hujjatlarni ko'ra oladi
        if self.has_role_type('faculty_dean') or self.has_role_type('dean_deputy'):
            faculty = self.managed_faculty or self.faculty
            if faculty and document.uploaded_by.faculty == faculty:
                return True
        
        # Kafedra mudiri o'z kafedrasidagi hujjatlarni ko'ra oladi
        if self.has_role_type('department_head'):
            department = self.managed_department or self.department
            if department and document.uploaded_by.department == department:
                return True
        
        # Hujjatni tasdiqlovchi bo'lsa
        if document.approval_steps.filter(approver=self).exists():
            return True
        
        return False
    
    def can_approve_document(self, document):
        """Hujjatni tasdiqlasha oladimi?"""
        current_step = document.get_current_approver()
        if current_step and current_step.status == 'pending':
            if current_step.approver == self:
                return True
            
            # Agar rollari bo'yicha tasdiqlash huquqi bo'lsa
            if current_step.role_required in self.get_role_types():
                return True
        
        return False
    
    def get_all_permissions(self):
        """Barcha ruxsatlarni olish"""
        permissions = set()
        role_types = self.get_role_types()
        
        # Har bir rol uchun ruxsatlarni yig'ish
        for role_type in role_types:
            if role_type == 'director':
                permissions.update(['view_all', 'approve_all', 'manage_users'])
            elif role_type == 'faculty_dean':
                permissions.update(['view_faculty', 'manage_faculty_documents'])
            elif role_type == 'department_head':
                permissions.update(['view_department', 'manage_subjects', 'manage_teachers'])
            elif role_type == 'teacher':
                permissions.update(['upload_documents', 'view_own_documents'])
            # ... boshqa rollar uchun
        
        return list(permissions)
    
    # ==================== DISPLAY METHODS ====================
    
    def get_active_role_display(self):
        """Faol rol nomini ko'rsatish"""
        if self.active_role:
            return self.active_role.name
        role_objs = self.get_role_objects()
        if role_objs:
            return role_objs[0].name
        return "Rol aniqlanmagan"
    
    def get_role_display(self):
        """Legacy uchun (oldingi kod bilan moslashish)"""
        return self.get_active_role_display()
    
    def get_full_name_with_roles(self):
        """FIO va rollarni birga"""
        full_name = self.get_full_name()
        roles = self.get_roles_display()
        return f"{full_name} ({roles})"
    
    def __str__(self):
        return self.get_full_name_with_roles()
    
    # ==================== SAVE METHODS ====================
    
    def save(self, *args, **kwargs):
        role_codes = self._get_role_codes()
        self.roles_data = ",".join(role_codes)

        if not self.active_role and role_codes:
            self.active_role = Role.get_role_by_code(role_codes[0])
        self._role_codes_cache = None
        self._role_objects_cache = None
        super().save(*args, **kwargs)
    
    # ==================== BULK ROLE MANAGEMENT ====================
    
    @classmethod
    def get_users_with_role_type(cls, role_type):
        """Berilgan rol tipidagi foydalanuvchilarni olish"""
        return cls.objects.filter(active_role__role_type=role_type)
    
    @classmethod
    def get_users_by_role_code(cls, role_code):
        """Berilgan rol kodidagi foydalanuvchilarni olish"""
        return cls.objects.filter(roles_data__regex=rf'(^|,){role_code}(,|$)')
       
        


class University(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'universitetlar'
        verbose_name_plural = 'Universities'
    
    def __str__(self):
        return self.name


class Faculty(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='faculties')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fakultetlar'
        verbose_name_plural = 'Fakultetlar'
        unique_together = [['university', 'code']]
    
    def __str__(self):
        return f"{self.name} - {self.university.name}"


class Department(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'Kafedralar'
        verbose_name_plural = 'Kafedralar'
        unique_together = [['faculty', 'code']]
    
    def __str__(self):
        return f"{self.name} - {self.faculty.name}"

'''
class Program(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    degree_level = models.CharField(max_length=50, choices=[
        ('bachelor', 'bakalavr'),
        ('master', 'magistr'),
        ('phd', 'PhD'),
    ])
    duration_years = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'programs'
        unique_together = [['department', 'code']]
    
    def __str__(self):
        return f"{self.name} ({self.get_degree_level_display()})"
'''

DEGREE_LEVELS=[
        ('bachelor', 'bakalavr'),
        ('master', 'magistr'),
        ('phd', 'PhD'),
    ]

class Program(models.Model):
    name = models.CharField(max_length=200, verbose_name="Yo'nalish nomi")
    code = models.CharField(max_length=20, unique=True, verbose_name="Yo'nalish kodi")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    degree_level = models.CharField(max_length=50, choices=DEGREE_LEVELS, default='bakalavr')
    duration_years = models.IntegerField(default=4, verbose_name="O'qish muddati (yil)")
    
    # education_type maydonini OLIB TASHLANG
    # education_type = models.CharField(...)  # BU QATORNI O'CHIRING
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'programs'
        verbose_name = "Yo'nalish"
        verbose_name_plural = "Yo'nalishlar"
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Group(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='groups')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'groups'
        verbose_name_plural = 'Guruhlar'
        unique_together = [['program', 'name']]
    
    def __str__(self):
        return f"{self.name} - {self.program.name}"

    @property
    def start_year(self):
        """Guruh qabul qilingan yilni olish (452-22 -> 2022)"""
        try:
            year_suffix = self.name.split('-')[-1]
            return 2000 + int(year_suffix)
        except Exception:
            return None

    @property
    def current_course(self):
        """Hozirgi vaqt uchun kursni hisoblash"""
        return self.get_course_for_year(timezone.now().year)
    
    def get_course_for_academic_year(self, academic_year_obj):
        """
        Berilgan o'quv yili uchun kursni hisoblash
        
        Masalan: 452-22 guruhi uchun
        - 2023-2024 o'quv yili: 2-kurs
        - 2024-2025 o'quv yili: 3-kurs  
        - 2025-2026 o'quv yili: 4-kurs
        """
        if not academic_year_obj or not isinstance(academic_year_obj, AcademicYear):
            return None
            
        return self.get_course_for_year(int(academic_year_obj.name.split('-')[0]))
    
    def get_course_for_year(self, target_year):
        """
        Berilgan yil uchun kursni hisoblash
        
        Formula: (O'quv yili boshlanishi) - (Guruh qabul yili) + 1
        
        Masalan:
        - Guruh: 452-22 (2022 qabul)
        - O'quv yili: 2025-2026 (2025 boshlanadi)
        - Kurs: 2025 - 2022 + 1 = 4-kurs
        """
        start = self.start_year
        if not start:
            return None
        
        # Kursni hisoblash
        course = target_year - start + 1
        
        # Kurs 1 dan kam bo'lmasin
        return max(course, 1)
    
    def get_course_display(self, academic_year=None):
        """Kursni ko'rsatish uchun formatlangan"""
        if academic_year:
            course = self.get_course_for_academic_year(academic_year)
        else:
            course = self.current_course
        
        if course:
            return f"{course}-kurs"
        return "Kurs aniqlanmadi"



class AcademicYear(models.Model):
    """O'quv yili (masalan: 2023-2024)"""
    name = models.CharField(max_length=20, unique=True)  # "2023-2024"
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'academic_years'
        verbose_name_plural = 'Oquv yili'
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class Subject(models.Model):
    """Fan modeli"""
    name = models.CharField(max_length=200, verbose_name="Fan nomi")
    code = models.CharField(max_length=20,  verbose_name="Fan kodi")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='subjects')
    
    # YANGI: Yo'nalishlar uchun CharField
    taught_in_programs = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Qaysi yo'nalishlarda o'tiladi",
        help_text="Yo'nalish kodlari vergul bilan ajratilgan. Masalan: BAA,DAA,TAA",
        default='TEMP' 
    )
    
    credits = models.IntegerField(default=3, verbose_name="Kredit")
    lecture_hours = models.IntegerField(default=30, verbose_name="Ma'ruza soatlari")
    practice_hours = models.IntegerField(default=30, verbose_name="Amaliyot soatlari")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subjects'
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    # Helper metodlar
    @property
    def programs_list(self):
        """Yo'nalish kodlarini list sifatida qaytarish"""
        if self.taught_in_programs:
            return [code.strip() for code in self.taught_in_programs.split(',') if code.strip()]
        return []
    
    @property
    def programs_display(self):
        """Ko'rsatish uchun formatlangan"""
        programs = self.programs_list
        if programs:
            return ", ".join(programs)
        return "—"
    
    def get_program_objects(self):
        """Yo'nalish obyektlarini olish (agar kerak bo'lsa)"""
        from .models import Program
        if self.programs_list and self.department:
            return Program.objects.filter(
                code__in=self.programs_list,
                department=self.department
            )
        return Program.objects.none()
    
    def has_program(self, program_code):
        """Berilgan yo'nalishda o'tiladimi?"""
        return program_code in self.programs_list


class TeachingAllocation(models.Model):
    """
    Fan taqsimoti: Kafedra mudiri qaysi o'qituvchiga, qaysi guruhda, 
    qaysi fandan dars berishini belgilaydi.
    """
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='allocations')
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teaching_allocations',
        limit_choices_to={'active_role__role_type': 'teacher'}
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='allocations')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='subject_allocations')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='allocations')
    
    semester = models.IntegerField(default=1, help_text="1, 2, 3...")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='allocations_created')

    class Meta:
        db_table = 'teaching_allocations'
        # Bir xil yil, semestr, guruh va fan uchun bitta o'qituvchi bo'lishi kerak
        unique_together = [['subject', 'group', 'academic_year', 'semester']]

    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.subject.name} ({self.group.name})"

# --------------------------------------------------------


class DocumentType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    max_file_size_mb = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    allowed_extensions = models.JSONField(default=list)
    
    approval_workflow = models.JSONField()
    deadline_hours = models.IntegerField(default=48)
    
    # Hujjat turi fanga yoki yilga bog'liqmi?
    requires_subject = models.BooleanField(default=False, help_text="Agar rost bo'lsa, hujjat yuklashda fan tanlash majburiy bo'ladi")
    requires_academic_year = models.BooleanField(default=False, help_text="Agar rost bo'lsa, hujjat yuklashda o'quv yili tanlash majburiy bo'ladi")
    requires_group = models.BooleanField(default=False, help_text="Agar rost bo'lsa, hujjat yuklashda guruh tanlash majburiy bo'ladi")
    
    # YANGI: Kimlar bu turdagi hujjat yuklashi mumkin
    allowed_roles = models.JSONField(
        default=list,
        help_text="Bu turdagi hujjat yuklashi mumkin bo'lgan rollar ro'yxati. Bo'sh bo'lsa, hamma yuklashi mumkin.",
        blank=True
    )
    # Masalan: ["teacher", "department_head", "faculty_dean"]
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_types'
        verbose_name_plural = 'Hujjat turlari'
    
    def __str__(self):
        return self.name
    
    def get_workflow_display(self):
        role_dict = dict(Role.ROLE_TYPE_CHOICES)

        return " → ".join([role_dict.get(role, role) for role in self.approval_workflow])
    
    def can_user_upload(self, user):
        """
        Foydalanuvchi bu turdagi hujjat yuklashi mumkinmi?
        """
        # Agar allowed_roles bo'sh bo'lsa, hamma yuklashi mumkin
        if not self.allowed_roles:
            return True
        
        user_role_types = user.get_role_types()
        return any(rt in self.allowed_roles for rt in user_role_types)
    
    def get_allowed_roles_display(self):
        
        if not self.allowed_roles:
            return "Hamma rollar"
        
        role_dict = dict(Role.ROLE_TYPE_CHOICES)
        return ", ".join([role_dict.get(role, role) for role in self.allowed_roles])


class Document(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uploaded_documents')
    
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    related_group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
  

    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    current_step = models.IntegerField(default=0)
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    verification_code = models.CharField(max_length=4, unique=True, editable=False)
    qr_code_image = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    final_pdf = models.FileField(upload_to='approved_documents/', null=True, blank=True)
    
    title = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents'
        verbose_name_plural = 'Hujjatlar'
        indexes = [
            models.Index(fields=['status', 'uploaded_by']),
            models.Index(fields=['document_type', 'status']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['uuid']),
        ]
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.uploaded_by.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.verification_code:
            self.verification_code = self._generate_verification_code()
        
        if not self.pk and self.status == 'uploaded':
            super().save(*args, **kwargs)
            has_pending = self._create_approval_steps()
            if not has_pending:
                self.status = 'approved'
                self.completed_at = timezone.now()
                self.save(update_fields=['status', 'completed_at'])
            else:
                self.status = 'pending_approval'
                self.save(update_fields=['status'])
            return
        
        super().save(*args, **kwargs)
    
    def _generate_verification_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            if not Document.objects.filter(verification_code=code).exists():
                return code
    
    def _create_approval_steps(self):
        workflow = self.document_type.approval_workflow or []
        if not workflow:
            return False
        for step_order, role in enumerate(workflow):
            approver = self._find_approver_for_role(role)
            status = 'pending'
            approved_at = None
            comment = ''
            if not approver:
                status = 'skipped'
                approved_at = timezone.now()
                comment = "Auto-skipped: approver not found"
            ApprovalStep.objects.create(
                document=self,
                step_order=step_order,
                approver=approver,
                role_required=role,
                deadline=timezone.now() + timedelta(hours=self.document_type.deadline_hours),
                status=status,
                approved_at=approved_at,
                comment=comment,
            )
        has_pending = self._advance_to_next_pending_step()
        return has_pending

    def _advance_to_next_pending_step(self):
        steps = self.approval_steps.all().order_by('step_order')
        for step in steps:
            if step.status == 'pending':
                Document.objects.filter(pk=self.pk).update(current_step=step.step_order)
                return True
        return False
    
    def _find_approver_for_role(self, role):
        uploader = self.uploaded_by
        
        if role == 'department_head':
            if uploader.department and hasattr(uploader.department, 'head'):
                return uploader.department.head
        
        elif role == 'faculty_dean':
            if uploader.faculty and hasattr(uploader.faculty, 'dean'):
                return uploader.faculty.dean
        
        elif role == 'dean_deputy':
            return User.objects.filter(active_role__role_type='dean_deputy', faculty=uploader.faculty).first()
        
        elif role == 'director':
            return User.objects.filter(active_role__role_type='director').first()
        
        elif role == 'director_deputy':
            return User.objects.filter(active_role__role_type='director_deputy').first()
        
        elif role in ['academic_office', 'registration_office']:
            return User.objects.filter(active_role__role_type=role).first()
        
        elif role == 'teacher':
            # Agar hujjat aniq bir fan va guruhga bog'langan bo'lsa, o'sha fandan dars beruvchini topamiz
            if self.subject and self.related_group and self.academic_year:
                allocation = TeachingAllocation.objects.filter(
                    subject=self.subject,
                    group=self.related_group,
                    academic_year=self.academic_year
                ).first()
                if allocation:
                    return allocation.teacher
            
            # Aks holda kafedradagi istalgan o'qituvchi (yoki bo'sh qoladi)
            return User.objects.filter(active_role__role_type='teacher', department=uploader.department).first()
        
        return None
    
    def get_current_approver(self):
        try:
            return self.approval_steps.get(step_order=self.current_step)
        except ApprovalStep.DoesNotExist:
            return None
    
    def get_expected_approver_text(self):
        if self.status == 'approved':
            return "Hujjat to'liq tasdiqlangan"
        
        if self.status == 'rejected':
            rejected_step = self.approval_logs.filter(action='rejected').last()
            if rejected_step:
                return f"Rad etildi:{rejected_step.approver.get_full_name()} ({rejected_step.approver.get_role_display()})"
            return "Hujjat rad etilgan"
        
        current_step = self.get_current_approver()
        if current_step:
            role_display = dict(Role.ROLE_TYPE_CHOICES).get(current_step.role_required, current_step.role_required)
            approver_name = current_step.approver.get_full_name() if current_step.approver else "Tasdiqlanmagan"
            if current_step.approver is None:
                return f"Kutilmoqda: {role_display}: tasdiqlovchi biriktirilmagan (avtomatik o'tkaziladi)"
            
            time_remaining = current_step.deadline - timezone.now()
            hours_remaining = int(time_remaining.total_seconds() / 3600)
            
            if hours_remaining < 0:
                time_text = "Muddati o'tdi (avtomatik tasdiqlash kutilmoqda)"
            elif hours_remaining < 24:
                time_text = f"{hours_remaining} soat qoldi"
            else:
                days = hours_remaining // 24
                time_text = f"{days} kun qoldi"
            
            return f"Kutilmoqda: {role_display}: {approver_name} ({time_text})"
        
        return "Workflow completed"
    
    def get_workflow_status(self):
        steps = []
        for approval_step in self.approval_steps.all().order_by('step_order'):
            step_info = {
                'order': approval_step.step_order + 1,
                'role': dict(Role.ROLE_TYPE_CHOICES).get(approval_step.role_required, approval_step.role_required),
                'approver': approval_step.approver.get_full_name() if approval_step.approver else 'Unassigned',
                'status': approval_step.status,
                'approved_at': approval_step.approved_at,
                'is_current': approval_step.step_order == self.current_step,
            }
            steps.append(step_info)
        return steps


class ApprovalStep(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('auto_approved', 'Auto-Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='approval_steps')
    step_order = models.IntegerField()
    approver = models.ForeignKey(User, on_delete=models.PROTECT, related_name='approval_tasks', null=True)
    role_required = models.CharField(max_length=30)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    deadline = models.DateTimeField()
    
    approved_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)
    
    class Meta:
        db_table = 'approval_steps'
        verbose_name_plural = 'Tasdiqlash bosqichlari'
        unique_together = [['document', 'step_order']]
        ordering = ['step_order']
    
    def __str__(self):
        return f"Step {self.step_order + 1} - {self.get_status_display()}"
    
    def is_overdue(self):
        return timezone.now() > self.deadline and self.status == 'pending'


class ApprovalLog(models.Model):
    ACTION_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('auto_approved', 'Auto-Approved'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='approval_logs')
    approval_step = models.ForeignKey(ApprovalStep, on_delete=models.CASCADE, related_name='logs')
    approver = models.ForeignKey(User, on_delete=models.PROTECT, related_name='approval_actions')
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    comment = models.TextField(blank=True, validators=[MinLengthValidator(20)])
    
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'approval_logs'
        verbose_name_plural = 'Tasdiqlash loglari'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.approver.get_full_name()} {self.action} - {self.timestamp}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('document_uploaded', 'Document Uploaded'),
        ('approval_needed', 'Approval Needed'),
        ('document_approved', 'Document Approved'),
        ('document_rejected', 'Document Rejected'),
        ('deadline_approaching', 'Deadline Approaching'),
        ('deadline_reminder', 'Deadline Reminder'),
        ('deadline_urgent', 'Deadline Urgent'),
        ('deadline_24h', 'Deadline 24H'),
        ('deadline_2h', 'Deadline 2H'),
        ('auto_approved', 'Auto-Approved'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    sent_email = models.BooleanField(default=False)
    sent_push = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name_plural = 'Bildirishnomalar'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('role_switched', 'Role Switched'),
        ('document_approved', 'Document Approved'),
        ('document_rejected', 'Document Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        user_label = self.user.username if self.user else "system"
        return f"{self.action} - {user_label} - {self.created_at}"


class RequestLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    method = models.CharField(max_length=10)
    path = models.TextField()
    query_string = models.TextField(blank=True)
    status_code = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.TextField(blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    request_body = models.JSONField(null=True, blank=True)
    request_bytes = models.IntegerField(null=True, blank=True)
    response_bytes = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'request_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['status_code']),
            models.Index(fields=['method']),
            models.Index(fields=['path']),
        ]

    def __str__(self):
        user_label = self.user.username if self.user else "anonymous"
        return f"{self.method} {self.path} - {self.status_code} - {user_label}"


class SecurityPolicy(models.Model):
    rate_limit_per_minute = models.IntegerField(default=30)
    burst = models.IntegerField(default=15)
    findtime_seconds = models.IntegerField(default=120)
    maxretry = models.IntegerField(default=3)
    bantime_seconds = models.IntegerField(default=-1)
    whitelist = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'security_policies'
        verbose_name = "Security Policy"
        verbose_name_plural = "Security Policies"

    def __str__(self):
        return f"SecurityPolicy #{self.pk}"

    def get_whitelist(self):
        raw = self.whitelist or ""
        tokens = []
        for part in raw.replace(",", "\n").splitlines():
            item = part.strip()
            if item:
                tokens.append(item)
        return tokens

    def get_ignoreip_value(self):
        return " ".join(self.get_whitelist())


class JobRun(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    task_name = models.CharField(max_length=200, unique=True)
    last_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    last_duration_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'job_runs'
        ordering = ['task_name']

    def __str__(self):
        return f"{self.task_name} - {self.last_status}"
