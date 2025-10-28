"""
Django settings for gather_ed project.
Optimized for performance and security.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()

# --------------------------
# Base Directory
# --------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------
# Security
# --------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-your-secret-key-here")

# Change this to False in production
DEBUG = False   # 👈 Change to True only when testing locally

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.vercel.app', '.render.com', '.onrender.com']

# --------------------------
# Installed Apps
# --------------------------
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

# --------------------------
# Middleware
# --------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ Speeds up static file loading
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --------------------------
# URL / WSGI
# --------------------------
ROOT_URLCONF = 'gather_ed.urls'
WSGI_APPLICATION = 'gather_ed.wsgi.application'

# --------------------------
# Templates
# --------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # global template folder
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

# --------------------------
# Database (Supabase)
# --------------------------
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=60,     # Keep connection alive for performance
        ssl_require=True,
    )
}

# --------------------------
# Password Validation
# --------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# --------------------------
# Localization
# --------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'   # ✅ Set to your local timezone
USE_I18N = True
USE_TZ = True

# --------------------------
# Static & Media Files
# --------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Keep this only if you have extra global static files (not per app)
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # You can create this if needed
]

# Serve static files efficiently
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --------------------------
# Caching (for speed)
# --------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'gathered-cache',
    }
}

# --------------------------
# Login & Redirects
# --------------------------
LOGIN_URL = 'events:login'
LOGIN_REDIRECT_URL = 'events:dashboard'
LOGOUT_REDIRECT_URL = 'events:login'

# --------------------------
# Email (Console for Dev)
# --------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'support@gathered.edu'

# --------------------------
# Supabase Keys
# --------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    print("⚠️ WARNING: SUPABASE_URL is missing in your .env file")

# --------------------------
# Default Primary Key
# --------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
