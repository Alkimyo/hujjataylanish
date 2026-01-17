
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import PasswordChangeForm
from .models import User
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model

from .models import Hujjat, DocumentType, Subject, AcademicYear, Group, TeachingAllocation,Program
User = get_user_model()



class DocumentUploadForm(forms.ModelForm):
    """Form for uploading documents with dynamic fields based on document type"""
    
    # Dinamik maydonlar
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        label="Fan",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Hujjat qaysi fanga tegishli"
    )
    
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.filter(is_active=True),
        required=False,
        label="O'quv yili",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Hujjat qaysi o'quv yiliga tegishli"
    )
    
    related_group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        required=False,
        label="Guruh",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Hujjat qaysi guruhga tegishli"
    )
    
    class Meta:
        model = Hujjat
        fields = ['document_type', 'subject', 'academic_year', 'related_group', 'file', 'title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Hujjat nomi'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Hujjat haqida qisqacha ma\'lumot...'
            }),
            'document_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'documentTypeSelect'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            })
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        if user:
            available_types = DocumentType.objects.filter(is_active=True)
            
            # Foydalanuvchi roliga qarab filtrlash
            user_allowed_types = []
            for doc_type in available_types:
                if doc_type.can_user_upload(user):
                    user_allowed_types.append(doc_type.id)
            
            self.fields['document_type'].queryset = DocumentType.objects.filter(
                id__in=user_allowed_types
            )
            
            # Fanlar ro'yxatini foydalanuvchi kafedrasiga qarab filtrlash
            if user.department:
                self.fields['subject'].queryset = Subject.objects.filter(
                    department=user.department
                )
            
            # Guruhlar ro'yxatini foydalanuvchi fakultetiga qarab filtrlash
            if user.faculty:
                self.fields['related_group'].queryset = Group.objects.filter(
                    program__department__faculty=user.faculty
                )
        
        # Labels
        self.fields['document_type'].label = "Hujjat turi"
        self.fields['document_type'].empty_label = "Hujjat turini tanlang..."
        self.fields['title'].label = "Hujjat nomi"
        self.fields['description'].label = "Ta'rif"
        self.fields['file'].label = "Fayl"
        
        # Hujjat turi tanlanganda dinamik maydonlarni ko'rsatish
        if self.data.get('document_type'):
            try:
                doc_type = DocumentType.objects.get(id=self.data.get('document_type'))
                self._set_field_requirements(doc_type)
            except DocumentType.DoesNotExist:
                pass
    
    def _set_field_requirements(self, doc_type):
        """Hujjat turiga qarab maydonlarni majburiy qilish"""
        self.fields['subject'].required = doc_type.requires_subject
        self.fields['academic_year'].required = doc_type.requires_academic_year
        self.fields['related_group'].required = doc_type.requires_group
    
    def clean(self):
        cleaned_data = super().clean()
        document_type = cleaned_data.get('document_type')
        
        if document_type:
            # Foydalanuvchi bu hujjat turini yuklashi mumkinmi?
            if self.user and not document_type.can_user_upload(self.user):
                raise ValidationError(
                    f"Sizning rolingiz ({self.user.get_role_display()}) "
                    f"'{document_type.name}' turida hujjat yuklashga ruxsati yo'q."
                )
            
            # Majburiy maydonlarni tekshirish
            if document_type.requires_subject and not cleaned_data.get('subject'):
                self.add_error('subject', 'Bu hujjat turi uchun fan tanlash majburiy')
            
            if document_type.requires_academic_year and not cleaned_data.get('academic_year'):
                self.add_error('academic_year', 'Bu hujjat turi uchun o\'quv yili tanlash majburiy')
            
            if document_type.requires_group and not cleaned_data.get('related_group'):
                self.add_error('related_group', 'Bu hujjat turi uchun guruh tanlash majburiy')
        
        return cleaned_data
    
    def clean_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('file')
        
        if not file:
            raise ValidationError("Iltimos, yuklash uchun faylni tanlang")
        
        # Get document type to check allowed extensions
        document_type = self.cleaned_data.get('document_type')
        
        if document_type:
            # Check file extension
            file_extension = file.name.split('.')[-1].lower()
            allowed_extensions = document_type.allowed_extensions
            
            if allowed_extensions and file_extension not in allowed_extensions:
                raise ValidationError(
                    f"'.{file_extension}' fayl kengaytmasiga ruxsat yo'q. "
                    f"Ruxsat etilgan kengaytmalar: {', '.join(allowed_extensions)}"
                )
            
            # Check file size
            max_size_bytes = float(document_type.max_file_size_mb) * 1024 * 1024
            if file.size > max_size_bytes:
                raise ValidationError(
                    f"Faylingiz hajmi ({file.size / 1024 / 1024:.2f}MB) "
                    f"maksimal ruxsat etilgan hajmdan ({document_type.max_file_size_mb}MB) oshdi."
                )
        
        return file



class ApprovalForm(forms.Form):
    """Form for approving documents"""
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Fikr bildirishingiz mumkin (ixtiyoriy)'
        }),
        label='Fikrlar'
    )


class RejectionForm(forms.Form):
    """Form for rejecting documents"""
    reason = forms.CharField(
        required=True,
        min_length=20,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Iltimos, rad etish sababini yozing (kamida 20 ta belgi)'
        }),
        label='Rad etish sababi',
        help_text='Kamida 20 ta belgi talab qilinadi'
    )
    
    def clean_reason(self):
        """Validate rejection reason"""
        reason = self.cleaned_data.get('reason', '').strip()
        
        if len(reason) < 20:
            raise ValidationError("Rad etish sababi 20 ta belgidan ko'p bo'lishi kerak")
        
        return reason


class DocumentFilterForm(forms.Form):
    """Form for filtering documents"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('uploaded', 'Uploaded'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(is_active=True),
        required=False,
        empty_label="All Hujjat Types",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by filename or uploader name'
        })
    )


class SubjectImportForm(forms.Form):
    file = forms.FileField(
        label="Fanlar fayli",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx'})
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise ValidationError("Fayl tanlang.")
        name = file.name.lower()
        if not (name.endswith('.csv') or name.endswith('.xlsx')):
            raise ValidationError("Faqat .csv yoki .xlsx fayllari qabul qilinadi.")
        return file


class AllocationImportForm(forms.Form):
    file = forms.FileField(
        label="Taqsimotlar fayli",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx'})
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise ValidationError("Fayl tanlang.")
        name = file.name.lower()
        if not (name.endswith('.csv') or name.endswith('.xlsx')):
            raise ValidationError("Faqat .csv yoki .xlsx fayllari qabul qilinadi.")
        return file


User = get_user_model()

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Eski parol",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        label="Yangi parol",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        label="Yangi parolni tasdiqlang",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )



class PasswordChangeUzForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Eski parol",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        label="Yangi parol",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        label="Yangi parolni tasdiqlang",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }



# forms.py
class SubjectForm(forms.ModelForm):
    """Fan qo'shish/tahrirlash formasi"""
    
    programs = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Qaysi yo'nalishlarda o'tiladi",
        help_text="Kafedraga tegishli yo'nalishlarni tanlang"
    )
    
    class Meta:
        model = Subject
        fields = ['name', 'code', 'credits', 'lecture_hours', 'practice_hours', 'programs']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'credits': forms.NumberInput(attrs={'class': 'form-control'}),
            'lecture_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'practice_hours': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.department = department
        
        # Kafedradagi yo'nalishlar ro'yxatini olish
        if department:
            # Faqat department bo'yicha filter (is_active ni olib tashlash)
            programs = Program.objects.filter(
                department=department
            ).order_by('code')
            
            # Checkboxlar uchun choices
            program_choices = [
                (p.code, f"{p.name}") 
                for p in programs
            ]
            self.fields['programs'].choices = program_choices
            
            # Tahrirlashda: avval tanlanganlarni o'rnatish
            if self.instance and self.instance.pk:
                selected_codes = self.instance.programs_list
                self.fields['programs'].initial = selected_codes
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Program kodlarini tekshirish
        programs = cleaned_data.get('programs', [])
        programs = [code.strip() for code in programs if code.strip()]
        programs = list(set(programs))
        
        # CharField ga saqlash
        cleaned_data['taught_in_programs'] = ','.join(programs) if programs else ''
        
        return cleaned_data



# forms.py
class TeachingAllocationForm(forms.ModelForm):
    """O'qituvchiga fan biriktirish formasi"""
    
    academic_year = forms.CharField(
        required=True,
        label="O'quv yili",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masalan: 2025-2026'
        }),
        help_text="O'quv yilini kiriting: 2025-2026"
    )
    
    class Meta:
        model = TeachingAllocation
        fields = ['teacher', 'subject', 'group', 'semester']
        widgets = {
            'teacher': forms.Select(attrs={
                'class': 'form-select',
            }),
            'subject': forms.Select(attrs={
                'class': 'form-select',
            }),
            'group': forms.Select(attrs={
                'class': 'form-select',
                'id': 'group_select'
            }),
            'semester': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '8',
                'placeholder': '1',
                'id': 'semester_input'
            }),
        }
        labels = {
            'teacher': 'O\'qituvchi',
            'subject': 'Fan',
            'group': 'Guruh',
            'semester': 'Semestr'
        }
    
    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.department = department
        
        if department:
            # Faqat kafedradagi o'qituvchilar
            self.fields['teacher'].queryset = User.objects.filter(
                active_role__role_type='teacher',
                department=department
            ).order_by('first_name', 'last_name')
            
            # Faqat kafedradagi fanlar
            self.fields['subject'].queryset = Subject.objects.filter(
                department=department
            ).order_by('name')
            
            # Faqat kafedraga tegishli yo'nalishdagi guruhlar
            if department.faculty:
                # Kafedraning yo'nalishlari (programlar)
                department_programs = Program.objects.filter(department=department)
                
                # Ushbu yo'nalishlardagi guruhlar
                self.fields['group'].queryset = Group.objects.filter(
                    program__in=department_programs
                ).order_by('name')
        
        # Instance bo'yicha boshlang'ich qiymat
        if self.instance and self.instance.pk and self.instance.academic_year:
            self.fields['academic_year'].initial = self.instance.academic_year.name
    
    def clean_academic_year(self):
        """O'quv yilini format tekshirish va bazaga saqlash"""
        academic_year_input = self.cleaned_data.get('academic_year', '').strip()
        
        if not academic_year_input:
            raise ValidationError("O'quv yilini kiriting")
        
        # Formatni tekshirish (masalan: 2025-2026)
        import re
        pattern = r'^\d{4}-\d{4}$'
        if not re.match(pattern, academic_year_input):
            raise ValidationError("O'quv yilini to'g'ri formatda kiriting: 2025-2026")
        
        # Yangi o'quv yili yaratish yoki mavjudini olish
        try:
            year_start = int(academic_year_input.split('-')[0])
            
            # Sana formatlash
            from datetime import date
            start_date = date(year_start, 9, 1)  # Sentabr 1
            end_date = date(year_start + 1, 5, 31)  # May 31
            
            # Bazadan qidirish yoki yaratish
            academic_year, created = AcademicYear.objects.get_or_create(
                name=academic_year_input,
                defaults={
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_active': True
                }
            )
            
            return academic_year
            
        except Exception as e:
            raise ValidationError(f"O'quv yili yaratishda xatolik: {str(e)}")
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Guruh va o'quv yilidan kursni hisoblash
        group = cleaned_data.get('group')
        academic_year = cleaned_data.get('academic_year')
        semester = cleaned_data.get('semester')
        
        if group and academic_year:
            # Guruh nomidan qabul qilingan yilni olish (354-20 -> 2020)
            group_name = group.name
            admission_year = None
            
            # Guruh nomidan yilni ajratish
            import re
            match = re.search(r'[-_](\d{2})$', group_name)  # Oxirgi 2 raqam
            if match:
                year_suffix = match.group(1)
                # 20 -> 2020, 21 -> 2021, 22 -> 2022
                admission_year = 2000 + int(year_suffix)
            
            if admission_year:
                # O'quv yilining boshlanish yilini olish (2025-2026 -> 2025)
                academic_year_start = int(academic_year.name.split('-')[0])
                
                # Kursni hisoblash
                course_number = academic_year_start - admission_year + 1
                
                # Kursni tekshirish
                if course_number < 1:
                    raise ValidationError(
                        f"Guruh {group.name} {admission_year}-yilda qabul qilingan. "
                        f"{academic_year.name} o'quv yilida hali o'qimaydi."
                    )
                elif course_number > 4:
                    raise ValidationError(
                        f"Guruh {group.name} {admission_year}-yilda qabul qilingan. "
                        f"{academic_year.name} o'quv yilida allaqachon bitirgan."
                    )
                
                # Semestrni kursga mosligini tekshirish
                if semester:
                    expected_min_semester = (course_number * 2) - 1  # 1-kurs -> 1-semestr
                    expected_max_semester = course_number * 2       # 1-kurs -> 2-semestr
                    
                    if semester < expected_min_semester or semester > expected_max_semester:
                        self.add_error(
                            'semester',
                            f"{course_number}-kurs uchun semestr {expected_min_semester}-"
                            f"{expected_max_semester} oralig'ida bo'lishi kerak."
                        )
        
        # Bir xil guruh, fan, yil va semestrga bitta o'qituvchi tekshiruvi
        subject = cleaned_data.get('subject')
        
        if subject and group and academic_year and semester:
            existing = TeachingAllocation.objects.filter(
                subject=subject,
                group=group,
                academic_year=academic_year,
                semester=semester
            )
            
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                teacher = existing.first().teacher
                raise ValidationError(
                    f"Bu guruhda, o'quv yilida va semestrda '{subject.name}' "
                    f"fanidan allaqachon {teacher.get_full_name()} dars beradi."
                )
        
        return cleaned_data



# forms.py

from django import forms
from .models import User, Role

class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['roles_data', 'active_role']
        widgets = {
            'roles_data': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Masalan: TEACHER_BASIC,DEPARTMENT_HEAD_BASIC',
                'class': 'form-control'
            }),
        }
    
    def clean_roles_data(self):
        data = self.cleaned_data['roles_data'] or ''
        try:
            role_codes = [code.strip() for code in str(data).split(',') if code.strip()]
            if not role_codes:
                return ''

            invalid_codes = [
                code for code in role_codes
                if not Role.objects.filter(code=code).exists()
            ]
            if invalid_codes:
                raise forms.ValidationError(
                    f"Noto'g'ri rol kodlari: {', '.join(invalid_codes)}"
                )

            return ",".join(role_codes)
        except Exception:
            raise forms.ValidationError("Rollarni to'g'ri formatda kiriting")
