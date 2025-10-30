"""
Django settings for gather_ed project.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================
# SECURITY & DEBUG
# =====================
SECRET_KEY = 'django-insecure-your-secret-key-here'
DEBUG = True
ALLOWED_HOSTS = []

# =====================
# INSTALLED APPS
# =====================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Your custom apps
    'apps',
    'apps.landing_page',
    'apps.register_page',
    'apps.login_page',
    'apps.admin_dashboard_page',
    'apps.student_dashboard_page',
]

# =====================
# MIDDLEWARE
# =====================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gather_ed.urls'

# =====================
# TEMPLATES
# =====================
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

WSGI_APPLICATION = 'gather_ed.wsgi.application'

# =====================
# DATABASE (Supabase)
# =====================
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,    # 10 minutes connection pooling
        ssl_require=True,
    )
}

# =====================
# PASSWORD VALIDATORS
# =====================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# =====================
# LANGUAGE / TIMEZONE
# =====================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =====================
# STATIC & MEDIA FILES
# =====================
STATIC_URL = 'static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'apps/landing_page'),
    os.path.join(BASE_DIR, 'apps/register_page'),
    os.path.join(BASE_DIR, 'apps/login_page'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =====================
# DEFAULT PRIMARY KEY
# =====================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================
# LOGIN CONFIG
# =====================
LOGIN_URL = 'events:login'
LOGIN_REDIRECT_URL = 'events:dashboard'
LOGOUT_REDIRECT_URL = 'events:login'

# =====================
# EMAIL (Console Debug)
# =====================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'support@gathered.edu'

# =====================
# SUPABASE SETTINGS
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    print("⚠️ WARNING: SUPABASE_URL missing in environment variables.")

# =====================
# SESSION & CACHING SETTINGS
# =====================
# Session engine using cache + DB fallback (fast & reliable)
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"

# Cache configuration (file-based cache for local use)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": BASE_DIR / "django_cache",
    }
}

# Auto logout after 6 hours (21600 seconds)
SESSION_COOKIE_AGE = 6 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# =====================
# STATIC FILE OPTIMIZATION
# =====================
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# ===============================
# 🔐 SESSION SECURITY CONFIGURATION
# ===============================

# Prevent client-side JavaScript from accessing the session cookie
SESSION_COOKIE_HTTPONLY = True

# Only send session cookies over HTTPS (keep True in production)
SESSION_COOKIE_SECURE = True

# CSRF and cross-site request protection
SESSION_COOKIE_SAMESITE = 'Lax'

# Session will last for 24 hours (86400 seconds)
SESSION_COOKIE_AGE = 86400  # 24 hours

# Extend session expiry on every request (active users stay logged in)
SESSION_SAVE_EVERY_REQUEST = True

# Do not delete the session when the browser closes
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Use database-backed sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ===============================
# ⏰ CLEANUP / AUTO LOGOUT LOGIC
# ===============================

# Maximum allowed inactivity before forced logout in cleanup command
SESSION_INACTIVITY_LIMIT_HOURS = 6

