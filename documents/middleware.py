import json
import logging
import time
from django.utils import timezone
from .models import Role, RequestLog


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


class AuditRequestMiddleware:
    """
    Full audit logger for HTTP requests.
    Writes JSON lines to a file and stores structured data in DB.
    """

    SENSITIVE_KEYS = {
        "password",
        "password1",
        "password2",
        "new_password",
        "old_password",
        "token",
        "csrfmiddlewaretoken",
    }

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("audit")

    def __call__(self, request):
        start = time.monotonic()
        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            try:
                self._log_request(request, response, start)
            except Exception:
                # Never break request flow if audit logging fails
                pass

    def _should_skip(self, path):
        return path.startswith("/static/") or path.startswith("/media/") or path == "/favicon.ico"

    def _redact(self, data):
        redacted = {}
        for key, value in data.items():
            if key.lower() in self.SENSITIVE_KEYS:
                redacted[key] = "***"
            else:
                redacted[key] = value
        return redacted

    def _extract_request_body(self, request):
        if request.method not in {"POST", "PUT", "PATCH"}:
            return None

        content_type = (request.content_type or "").lower()
        if "application/json" in content_type:
            try:
                payload = json.loads(request.body.decode("utf-8"))
                if isinstance(payload, dict):
                    return self._redact(payload)
                return payload
            except Exception:
                return None

        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            data = {k: request.POST.getlist(k) if len(request.POST.getlist(k)) > 1 else request.POST.get(k)
                    for k in request.POST.keys()}
            data = self._redact(data)
            if request.FILES:
                files = {}
                for key, file in request.FILES.items():
                    files[key] = {"name": file.name, "size": file.size}
                data["files"] = files
            return data

        return None

    def _log_request(self, request, response, start):
        path = request.path or ""
        if self._should_skip(path):
            return

        duration_ms = int((time.monotonic() - start) * 1000)
        user = getattr(request, "user", None)
        user_obj = user if getattr(user, "is_authenticated", False) else None

        request_body = self._extract_request_body(request)
        response_status = getattr(response, "status_code", 0)
        response_bytes = None
        if response is not None and response.has_header("Content-Length"):
            try:
                response_bytes = int(response["Content-Length"])
            except Exception:
                response_bytes = None

        log_entry = {
            "timestamp": timezone.now().isoformat(),
            "method": request.method,
            "path": path,
            "query_string": request.META.get("QUERY_STRING", ""),
            "status_code": response_status,
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "referrer": request.META.get("HTTP_REFERER", ""),
            "duration_ms": duration_ms,
            "user": user_obj.username if user_obj else None,
        }
        if request_body is not None:
            log_entry["request_body"] = request_body

        self.logger.info(json.dumps(log_entry, ensure_ascii=False))

        RequestLog.objects.create(
            user=user_obj,
            method=request.method,
            path=path,
            query_string=request.META.get("QUERY_STRING", ""),
            status_code=response_status,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referrer=request.META.get("HTTP_REFERER", ""),
            duration_ms=duration_ms,
            request_body=request_body,
            request_bytes=request.META.get("CONTENT_LENGTH") or None,
            response_bytes=response_bytes,
        )
