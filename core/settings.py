# -----------------------------------------------------------------------------
# DJANGO PRODUCTION SETTINGS FOR RENOCORP
# -----------------------------------------------------------------------------
import os
import logging
from pathlib import Path
from celery.schedules import crontab
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
# CORE SETTINGS (SAFE)
# -----------------------------------------------------------------------------
SECRET_KEY = env('SECRET_KEY', default='unsafe-dev-key-change-me')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['renocorpinvestments.onrender.com', 'localhost', '127.0.0.1'])

CSRF_TRUSTED_ORIGINS = [
    f"https://{host.strip()}" for host in ALLOWED_HOSTS if host.strip() not in ['localhost', '127.0.0.1']
]

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

ADMIN_USERNAME = env('ADMIN_USERNAME', default='')
ADMIN_PASSWORD = env('ADMIN_PASSWORD', default='')

# -----------------------------------------------------------------------------
# EMAIL CONFIGURATION (SAFE)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'no-reply@example.com'

# -----------------------------------------------------------------------------
# DATABASE CONFIGURATION (SAFE)
# -----------------------------------------------------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL', default='sqlite:///' + str(BASE_DIR / 'db.sqlite3')),
        conn_max_age=600,
        ssl_require=False
    )
}

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

    'rest_framework',
    'drf_yasg',
    'django_celery_beat',
    'django_celery_results',
    'django_extensions',
    'django_compressor',

    'apps.dashboard.apps.DashboardConfig',
    'apps.admin_panel.apps.AdminPanelConfig',
    'apps.ai_core.apps.AiCoreConfig',
    'apps.accounts.apps.AccountsConfig',
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
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# -----------------------------------------------------------------------------
# TEMPLATES
# -----------------------------------------------------------------------------
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
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
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# -----------------------------------------------------------------------------
# CELERY
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Kampala'

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
# FLUTTERWAVE (SAFE)
# -----------------------------------------------------------------------------
FLUTTERWAVE_PUBLIC_KEY = env('FLUTTERWAVE_PUBLIC_KEY', default='')
FLUTTERWAVE_SECRET_KEY = env('FLUTTERWAVE_SECRET_KEY', default='')
FLUTTERWAVE_ENCRYPTION_KEY = env('FLUTTERWAVE_ENCRYPTION_KEY', default='')

# Enable payments only if the key exists
FEATURE_PAYMENTS_ENABLED = bool(FLUTTERWAVE_PUBLIC_KEY)

# Optional: warn in logs if the key is missing
if FEATURE_PAYMENTS_ENABLED:
    print("💳 Flutterwave payments are enabled.")
else:
    print("⚠️ Flutterwave public key not set. Payments are disabled.")

# -----------------------------------------------------------------------------
# OFFERWALLS (ALL SAFE)
# -----------------------------------------------------------------------------
USD_TO_UGX_RATE = env.int('USD_TO_UGX_RATE', default=3800)
CPALEAD_PUBLISHER_ID = env('CPALEAD_PUBLISHER_ID', default='')
ADGATE_WALL_CODE = env('ADGATE_WALL_CODE', default='')
WANNADS_API_SECRET = env('WANNADS_API_SECRET', default='')
ADSCEND_PUBLISHER_ID = env('ADSCEND_PUBLISHER_ID', default='')
ADSCEND_WALL_ID = env('ADSCEND_WALL_ID', default='')
ADGEM_API_TOKEN = env('ADGEM_API_TOKEN', default='')
OFFERTORO_API_KEY = env('OFFERTORO_API_KEY', default='')

# -----------------------------------------------------------------------------
# FINANCIAL
# -----------------------------------------------------------------------------
MAX_SINGLE_WITHDRAWAL = env.int('MAX_SINGLE_WITHDRAWAL', default=100000)
DAILY_WITHDRAWAL_LIMIT = env.int('DAILY_WITHDRAWAL_LIMIT', default=400000)

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': logging.INFO},
}
ADMIN_PASSWORD = env('ADMIN_PASSWORD')

# -----------------------------------------------------------------------------
# EMAIL CONFIGURATION
# -----------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# -----------------------------------------------------------------------------
# DATABASE CONFIGURATION
# -----------------------------------------------------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL', default='sqlite:///' + str(BASE_DIR / 'db.sqlite3')),
        conn_max_age=600,
        ssl_require=True
    )
}

# -----------------------------------------------------------------------------
# INSTALLED APPS
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'drf_yasg',
    'django_celery_beat',
    'django_celery_results',
    'django_extensions',
    'django_compressor',

    # Project apps (inside apps/)
    'apps.dashboard.apps.DashboardConfig',
    'apps.admin_panel.apps.AdminPanelConfig',
    'apps.ai_core.apps.AiCoreConfig',
    'apps.accounts.apps.AccountsConfig',
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
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# -----------------------------------------------------------------------------
# TEMPLATES
# -----------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# -----------------------------------------------------------------------------
# PASSWORD VALIDATION
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------------------------------------------------------
# INTERNATIONALIZATION
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kampala'
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# STATIC & MEDIA FILES
# -----------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# -----------------------------------------------------------------------------
# CACHE
# -----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# -----------------------------------------------------------------------------
# CELERY CONFIGURATION
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Kampala'

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
# REST FRAMEWORK SETTINGS
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}

# -----------------------------------------------------------------------------
# FLUTTERWAVE & TASK PROVIDERS
# -----------------------------------------------------------------------------
FLUTTERWAVE_PUBLIC_KEY = env('FLUTTERWAVE_PUBLIC_KEY', default='')
FLUTTERWAVE_SECRET_KEY = env('FLUTTERWAVE_SECRET_KEY', default='')
FLUTTERWAVE_ENCRYPTION_KEY = env('FLUTTERWAVE_ENCRYPTION_KEY', default='')
# -----------------------------------------------------------------------------
# AI_core / Offerwall Providers
# -----------------------------------------------------------------------------
USD_TO_UGX_RATE = env.int('USD_TO_UGX_RATE', default=3800)

# CPALead
CPALEAD_IFRAME_BASE_URL = env('CPALEAD_IFRAME_BASE_URL', default='https://www.cpalead.com/iframe')
CPALEAD_PUBLISHER_ID = env('CPALEAD_PUBLISHER_ID', default='')

# AdGate
ADGATE_IFRAME_BASE_URL = env('ADGATE_IFRAME_BASE_URL', default='https://www.adgate.com/iframe')
ADGATE_WALL_CODE = env('ADGATE_WALL_CODE', default='')

# Wannads
WANNADS_IFRAME_BASE_URL = env('WANNADS_IFRAME_BASE_URL', default='https://api.wannads.com/iframe')
WANNADS_API_SECRET = env('WANNADS_API_SECRET', default='')

# Adscend
ADSCEND_IFRAME_BASE_URL = env('ADSCEND_IFRAME_BASE_URL', default='https://www.adscendmedia.com/iframe')
ADSCEND_PUBLISHER_ID = env('ADSCEND_PUBLISHER_ID', default='')
ADSCEND_WALL_ID = env('ADSCEND_WALL_ID', default='')

# AdGem
ADGEM_API_TOKEN = env('ADGEM_API_TOKEN', default='')
ADGEM_POSTBACK_KEY = env('ADGEM_POSTBACK_KEY', default='')
ADGEM_API_BASE_URL = env('ADGEM_API_BASE_URL', default='https://api.adgem.com/offers')

# Offertoro
OFFERTORO_API_KEY = env('OFFERTORO_API_KEY', default='')
OFFERTORO_SECRET_KEY = env('OFFERTORO_SECRET_KEY', default='')
OFFERTORO_BASE_URL = env('OFFERTORO_BASE_URL', default='')

# Additional Offerwalls
ADGATE_API_KEY = env('ADGATE_API_KEY', default='')
ADGATE_SECRET_KEY = env('ADGATE_SECRET_KEY', default='')
ADD_API_KEY = env('ADD_API_KEY', default='')
ADD_SECRET_KEY = env('ADD_SECRET_KEY', default='')
CPALEAD_API_KEY = env('CPALEAD_API_KEY', default='')
CPALEAD_SECRET_KEY = env('CPALEAD_SECRET_KEY', default='')

# -----------------------------------------------------------------------------
# FINANCIAL LIMITS
# -----------------------------------------------------------------------------
MAX_SINGLE_WITHDRAWAL = env.int('MAX_SINGLE_WITHDRAWAL', default=100000)
DAILY_WITHDRAWAL_LIMIT = env.int('DAILY_WITHDRAWAL_LIMIT', default=400000)

# -----------------------------------------------------------------------------
# DEFAULT CURRENCY & EXCHANGE
# -----------------------------------------------------------------------------
DEFAULT_CURRENCY = "UGX"
EXCHANGE_RATES = {"USD": 3800.0, "KES": 30.0, "UGX": 1.0, "EUR": 4100.0}

# -----------------------------------------------------------------------------
# SUPPORT INFO
# -----------------------------------------------------------------------------
SUPPORT_PHONE = env('SUPPORT_PHONE', default='+256753310698')

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': logging.INFO},
}
