"""
Django settings for gather_ed project.
"""

import os
from pathlib import Path
import dj_database_url
from django.contrib import staticfiles
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS","127.0.0.1,localhost").split(",") if h.strip()]
RENDER_EXTENAL_HOSTNAME = os.getenv("RENDER_EXTENAL_HOSTNAME")
if RENDER_EXTENAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTENAL_HOSTNAME)


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps',
    'apps.landing_page',
    'apps.register_page',
    'apps.login_page',
    'apps.admin_dashboard_page',
    'apps.student_dashboard_page'

]

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

# Database configuration using Supabase Session Pooler
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=60,   # keep DB connections alive for performance
        ssl_require=True,  # enforce SSL
    )
}

# Password validation
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

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'

# This is where Django will look for your static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'apps/landing_page'),
    os.path.join(BASE_DIR, 'apps/register_page'),
    os.path.join(BASE_DIR, 'apps/login_page'),

]

# This is the destination folder for collect static
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = 'events:login'
LOGIN_REDIRECT_URL = 'events:dashboard'
LOGOUT_REDIRECT_URL = 'events:login'

#Prints emails to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'support@gathered.edu'  # Any dummy for console

# Get the URL
SUPABASE_URL = os.environ.get("SUPABASE_URL")
if not SUPABASE_URL:
    # Use a method that logs an error or raises an exception if the key is mandatory
    print("FATAL ERROR: SUPABASE_URL is missing in environment variables.")

# 2. Get the Public/Anon Key (Used for read-only RLS checks)
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

# 3. Get the Service Role Key (Used for database writes in Django backend)
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")