"""
Django settings for gather_ed project.
"""

import os
from pathlib import Path
import dj_database_url
from django.contrib import staticfiles
from dotenv import load_dotenv

# Load environment variables from .env (for local dev)
load_dotenv()

# =====================
# PATHS
# =====================
BASE_DIR = Path(__file__).resolve().parent.parent

# =====================
# SECURITY & DEBUG
# =====================
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here')

# DEBUG is False by default unless explicitly set to True
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    'csit327-g7-gathered.onrender.com',
    'localhost',
    '127.0.0.1',
]

# Add Render's dynamic hostname if available
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# =====================
# APPLICATIONS
# =====================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Your apps
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
    'whitenoise.middleware.WhiteNoiseMiddleware',  # for static files on Render
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
            'debug': DEBUG,  # auto-disable in production
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
        conn_max_age=60,
        ssl_require=True,
    )
}

# =====================
# PASSWORD VALIDATION
# =====================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'apps.register_page.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# =====================
# INTERNATIONALIZATION
# =====================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# =====================
# STATIC & MEDIA FILES
# =====================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =====================
# AUTH & LOGIN
# =====================
LOGIN_URL = 'events:login'
LOGIN_REDIRECT_URL = 'events:dashboard'
LOGOUT_REDIRECT_URL = 'events:login'

# =====================
# EMAIL (SendGrid API - NO SMTP)
# =====================
# Console backend for development - emails print to terminal
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'gathered.cit.edu@gmail.com'

# Note: We're NOT using SMTP at all. SendGrid API is used directly in utils.py
# No EMAIL_HOST, EMAIL_PORT, etc. needed

# =====================
# SUPABASE KEYS
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "event-images")

if not SUPABASE_URL:
    print("⚠️ WARNING: SUPABASE_URL missing in environment variables.")

# =====================
# SESSION SECURITY & CONFIGURATION (6 HOURS)
# =====================
SESSION_COOKIE_HTTPONLY = True      # JS can't read session cookies
SESSION_COOKIE_SAMESITE = 'Lax'     # Protects against CSRF
SESSION_COOKIE_AGE = 6 * 60 * 60    # 6 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Secure cookies only in production
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# =====================
# PERFORMANCE OPTIMIZATIONS
# =====================
WHITENOISE_MAX_AGE = 31536000  # 1 year cache
CONN_MAX_AGE = 60
WHITENOISE_USE_FINDERS = True

# =====================
# DEFAULT PRIMARY KEY
# =====================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'