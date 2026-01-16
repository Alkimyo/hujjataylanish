from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    # Dashboard
    path('', RedirectView.as_view(url='dashboard/', permanent=False)),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        template_name='documents/logout.html'
    ), name='logout'),
     path('profile/', views.profile_view, name='profile'),

    # Document management
    path('documents/', views.document_list, name='document_list'),
    path('documents/<int:document_id>/', views.document_detail, name='document_detail'),
    path('documents/upload/', views.upload_document, name='upload_document'),
    path('documents/<int:document_id>/download/', views.download_document, name='download_document'),
    path('documents/<int:document_id>/qr/', views.download_qr_code, name='download_qr_code'),
    path('subject-distribution/', views.subject_distribution, name='subject_distribution'),
    path('api/document-type/<int:doc_type_id>/', views.get_document_type_info, name='get_document_type_info'),
    
    # Approval actions
    path('documents/<int:document_id>/approve/', views.approve_document, name='approve_document'),
    path('documents/<int:document_id>/reject/', views.reject_document, name='reject_document'),
    path('approvals/pending/', views.pending_approvals, name='pending_approvals'),
    
    # Verification (public)
    path('verify/', views.verify_document, name='verify_document'),
    path('verify/<uuid:uuid>/', views.verify_by_uuid, name='verify_by_uuid'),
    
    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # API endpoints
    path('api/documents/<int:document_id>/status/', views.api_document_status, name='api_document_status'),
    path('api/notifications/count/', views.api_notification_count, name='api_notification_count'),
    path('api/notifications/stream/', views.api_notification_stream, name='api_notification_stream'),
    path('api/jobs/health/', views.jobs_health, name='jobs_health'),
     path('department-head/', views.department_head_dashboard, name='department_head_dashboard'),
    
    # Fanlar boshqaruvi
    path('department-head/subjects/', views.subjects_list, name='subjects_list'),
    path('department-head/subjects/add/', views.subject_add, name='subject_add'),
    path('department-head/subjects/import/', views.subjects_import, name='subjects_import'),
    path('department-head/subjects/<int:subject_id>/edit/', views.subject_edit, name='subject_edit'),
    path('department-head/subjects/<int:subject_id>/delete/', views.subject_delete, name='subject_delete'),
    path('switch-role/', views.switch_role, name='switch_role'),
    # Fan taqsimotlari
    path('department-head/allocations/', views.allocations_list, name='allocations_list'),
    path('department-head/allocations/add/', views.allocation_add, name='allocation_add'),
    path('department-head/allocations/import/', views.allocations_import, name='allocations_import'),
    path('department-head/allocations/<int:allocation_id>/delete/', views.allocation_delete, name='allocation_delete'),
]
