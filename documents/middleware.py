from .models import Role


class ActiveRoleMiddleware:
    """
    Load active role from session and attach it to request.user.
    """

    SESSION_ROLE_CODE_KEY = "active_role_code"
    SESSION_ROLE_NAME_KEY = "current_role"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            role_obj = self._get_role_from_session(request)
            if role_obj and (user.has_role(role_obj.code) or user.has_role_type(role_obj.role_type)):
                user.active_role = role_obj
            else:
                request.session.pop(self.SESSION_ROLE_CODE_KEY, None)
                if not user.active_role:
                    role_codes = user._get_role_codes()
                    if role_codes:
                        user.active_role = Role.get_role_by_code(role_codes[0])
                        user.save(update_fields=['active_role'])
            user._get_role_codes()
            user.get_role_objects()
        return self.get_response(request)

    def _get_role_from_session(self, request):
        role_code = request.session.get(self.SESSION_ROLE_CODE_KEY)
        if role_code:
            return Role.get_role_by_code(role_code)

        role_name = request.session.get(self.SESSION_ROLE_NAME_KEY)
        if role_name:
            return Role.objects.filter(name__iexact=role_name, is_active=True).first()

        return None
