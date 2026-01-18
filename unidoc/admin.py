from django.contrib.admin import AdminSite
from django.http import HttpResponseForbidden
from django.contrib import admin as django_admin


class RoleAdminSite(AdminSite):
    site_header = "UniDoc Admin"
    site_title = "UniDoc Admin"
    index_title = "Boshqaruv paneli"

    def _has_admin_role(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        try:
            active_type = user.get_active_role_type()
            if active_type == "admin":
                return True
        except Exception:
            pass
        try:
            return user.has_role_type("admin")
        except Exception:
            return False

    def has_permission(self, request):
        return self._has_admin_role(request.user)

    def admin_view(self, view, cacheable=False):
        inner = super().admin_view(view, cacheable=cacheable)

        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and not self.has_permission(request):
                return HttpResponseForbidden("Forbidden")
            return inner(request, *args, **kwargs)

        return wrapper


admin_site = RoleAdminSite()
admin_site._registry = django_admin.site._registry
