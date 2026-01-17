
from pathlib import Path
import os
from urllib.parse import urlparse
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-insecure-change-me",
)

def _env_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

def _normalize_csrf_origin(origin):
    origin = origin.strip()
    if not origin:
        return None
    parsed = urlparse(origin)
    if parsed.scheme:
        return origin
    return f"https://{origin}"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool(os.getenv("DEBUG"), default=True)

allowed_hosts_raw = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(",") if host.strip(),'0.0.0.0']

csrf_origins_raw = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if csrf_origins_raw:
    CSRF_TRUSTED_ORIGINS = []
    for raw_origin in csrf_origins_raw.split(","):
        normalized_origin = _normalize_csrf_origin(raw_origin)
        if normalized_origin:
            CSRF_TRUSTED_ORIGINS.append(normalized_origin)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'documents.apps.DocumentsConfig',
    'import_export',
    'widget_tweaks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'documents.middleware.ActiveRoleMiddleware',
    'documents.middleware.AuditRequestMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'unidoc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'documents.context_processors.sidebar_permissions',
            ],
        },
    },
]

WSGI_APPLICATION = 'unidoc.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

default_db = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.getenv('DB_NAME'),
    'USER': os.getenv('DB_USER'),
    'PASSWORD': os.getenv('DB_PASSWORD'),
    'HOST': os.getenv('DB_HOST'),
    'PORT': os.getenv('DB_PORT'),
}
DATABASES = {
    'default': dj_database_url.config(default=None) or default_db
}



# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

AUTH_USER_MODEL = "documents.User"   # app nomingizga mos bo‘lsin


LOGIN_REDIRECT_URL = '/dashboard/'  

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / "media")))

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")

if S3_ENDPOINT_URL and S3_BUCKET_NAME and S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_ACCESS_KEY_ID = S3_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = S3_SECRET_ACCESS_KEY
    AWS_STORAGE_BUCKET_NAME = S3_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = S3_ENDPOINT_URL
    AWS_S3_REGION_NAME = os.getenv("S3_REGION", "")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_ADDRESSING_STYLE = "path"
    AWS_DEFAULT_ACL = "public-read"
    AWS_QUERYSTRING_AUTH = False
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@unidocs.uz')

SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', '900'))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = _env_bool(os.getenv('EMAIL_USE_TLS'), default=True)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

render_external_url = os.getenv('RENDER_EXTERNAL_URL', '')
if render_external_url:
    parsed = urlparse(render_external_url)
    if parsed.hostname:
        if parsed.hostname not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(parsed.hostname)
        if not csrf_origins_raw:
            normalized_origin = _normalize_csrf_origin(render_external_url)
            if normalized_origin:
                CSRF_TRUSTED_ORIGINS = [normalized_origin]
        if SITE_URL == 'http://localhost:8000':
            SITE_URL = render_external_url

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '%(message)s',
        },
    },
    'handlers': {
        'audit_file': {
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'audit.log',
            'formatter': 'json',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

if not DEBUG:
    if SECRET_KEY == "dev-insecure-change-me":
        raise RuntimeError("SECRET_KEY must be set in production.")

    SECURE_SSL_REDIRECT = _env_bool(os.getenv("SECURE_SSL_REDIRECT"), default=True)
    SESSION_COOKIE_SECURE = _env_bool(os.getenv("SESSION_COOKIE_SECURE"), default=True)
    CSRF_COOKIE_SECURE = _env_bool(os.getenv("CSRF_COOKIE_SECURE"), default=True)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool(
        os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS"), default=True
    )
    SECURE_HSTS_PRELOAD = _env_bool(os.getenv("SECURE_HSTS_PRELOAD"), default=True)
