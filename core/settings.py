# -----------------------------------------------------------------------------
# DJANGO PRODUCTION SETTINGS FOR RENOCORP (FAST + FULL)
# -----------------------------------------------------------------------------
import os
import logging
from pathlib import Path
import environ
import dj_database_url

# -----------------------------------------------------------------------------
# BASE DIRECTORY
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# ENVIRONMENT VARIABLES (.env)
# -----------------------------------------------------------------------------
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

# -----------------------------------------------------------------------------
# CORE SETTINGS
# -----------------------------------------------------------------------------
SECRET_KEY = env('SECRET_KEY', default='unsafe-dev-key-change-me')
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=['renocorpinvestiments-lwc8.onrender.com', 'localhost', '127.0.0.1']
)

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS
    if host not in ['localhost', '127.0.0.1']
]

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

ADMIN_USERNAME = env('ADMIN_USERNAME', default='')
ADMIN_PASSWORD = env('ADMIN_PASSWORD', default='')

# -----------------------------------------------------------------------------
# CSP
# -----------------------------------------------------------------------------
CSP_DEFAULT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:", "https://ui-avatars.com")
CSP_STYLE_SRC = ("'self'", "https:", "'unsafe-inline'")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")

# -----------------------------------------------------------------------------
# DATABASE (pooled for speed)
# -----------------------------------------------------------------------------
DATABASE_URL = env('DATABASE_URL', default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'))

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=DATABASE_URL.startswith("postgres")
    )
}

# -----------------------------------------------------------------------------
# REDIS CACHE (sessions + queries + dashboard)
# -----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# -----------------------------------------------------------------------------
# AUTH
# -----------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    'apps.accounts.auth_backend.FastAuthBackend',
    'django.contrib.auth.backends.ModelBackend'
]

LOGIN_URL = "/login/"
LOGOUT_REDIRECT_URL = "/login/"

# -----------------------------------------------------------------------------
# INSTALLED APPS
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'csp',

    'rest_framework',
    'drf_yasg',
    'django_celery_beat',
    'django_celery_results',
    'django_extensions',

    'apps.dashboard',
    'apps.admin_panel',
    'apps.ai_core',
    'apps.accounts',
]

# -----------------------------------------------------------------------------
# MIDDLEWARE
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# -----------------------------------------------------------------------------
# TEMPLATES (cached = instant)
# -----------------------------------------------------------------------------
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'OPTIONS': {
        'loaders': [
            (
                'django.template.loaders.cached.Loader',
                [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ],
            )
        ],
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

# -----------------------------------------------------------------------------
# INTERNATIONALIZATION
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kampala'
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# STATIC & MEDIA
# -----------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------------------------------------------------------
# CELERY (lazy load so web is fast)
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = env('REDIS_URL', default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Kampala"

if os.getenv("RUN_MAIN") == "true":
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        'daily_task_refresh': {
            'task': 'apps.ai_core.tasks.scheduled_daily_task_refresh',
            'schedule': crontab(hour=0, minute=0),
        },
        'reconcile_withdrawals_every_10min': {
            'task': 'apps.ai_core.tasks.reconcile_pending_transactions',
            'schedule': crontab(minute='*/10'),
        },
    }

# -----------------------------------------------------------------------------
# REST
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}

# -----------------------------------------------------------------------------
# PAYMENTS
# -----------------------------------------------------------------------------
FLUTTERWAVE_PUBLIC_KEY = env('FLUTTERWAVE_PUBLIC_KEY', default='')
FLUTTERWAVE_SECRET_KEY = env('FLUTTERWAVE_SECRET_KEY', default='')
FLUTTERWAVE_ENCRYPTION_KEY = env('FLUTTERWAVE_ENCRYPTION_KEY', default='')
USD_TO_UGX_RATE = env.int('USD_TO_UGX_RATE', default=3800)

# -----------------------------------------------------------------------------
# OFFERWALLS
# -----------------------------------------------------------------------------
CPALEAD_IFRAME_BASE_URL = env('CPALEAD_IFRAME_BASE_URL', default='https://www.cpalead.com/iframe')
CPALEAD_PUBLISHER_ID = env('CPALEAD_PUBLISHER_ID', default='')
ADGATE_IFRAME_BASE_URL = env('ADGATE_IFRAME_BASE_URL', default='https://www.adgate.com/iframe')
ADGATE_WALL_CODE = env('ADGATE_WALL_CODE', default='')
WANNADS_IFRAME_BASE_URL = env('WANNADS_IFRAME_BASE_URL', default='https://api.wannads.com/iframe')
WANNADS_API_SECRET = env('WANNADS_API_SECRET', default='')
ADSCEND_IFRAME_BASE_URL = env('ADSCEND_IFRAME_BASE_URL', default='https://www.adscendmedia.com/iframe')
ADSCEND_PUBLISHER_ID = env('ADSCEND_PUBLISHER_ID', default='')
ADSCEND_WALL_ID = env('ADSCEND_WALL_ID', default='')
ADGEM_API_TOKEN = env('ADGEM_API_TOKEN', default='')
ADGEM_POSTBACK_KEY = env('ADGEM_POSTBACK_KEY', default='')
ADGEM_API_BASE_URL = env('ADGEM_API_BASE_URL', default='https://api.adgem.com/offers')
OFFERTORO_API_KEY = env('OFFERTORO_API_KEY', default='')
OFFERTORO_SECRET_KEY = env('OFFERTORO_SECRET_KEY', default='')
OFFERTORO_BASE_URL = env('OFFERTORO_BASE_URL', default='')
ADGATE_API_KEY = env('ADGATE_API_KEY', default='')
ADGATE_SECRET_KEY = env('ADGATE_SECRET_KEY', default='')
ADD_API_KEY = env('ADD_API_KEY', default='')
ADD_SECRET_KEY = env('ADD_SECRET_KEY', default='')
CPALEAD_API_KEY = env('CPALEAD_API_KEY', default='')
CPALEAD_SECRET_KEY = env('CPALEAD_SECRET_KEY', default='')

# -----------------------------------------------------------------------------
# FINANCIAL
# -----------------------------------------------------------------------------
MAX_SINGLE_WITHDRAWAL = env.int('MAX_SINGLE_WITHDRAWAL', default=100000)
DAILY_WITHDRAWAL_LIMIT = env.int('DAILY_WITHDRAWAL_LIMIT', default=400000)

DEFAULT_CURRENCY = "UGX"
EXCHANGE_RATES = {"USD": 3800.0, "KES": 30.0, "UGX": 1.0, "EUR": 4100.0}

SUPPORT_PHONE = env('SUPPORT_PHONE', default='+256753310698')

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
