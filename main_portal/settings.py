import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add TPM Portal, CMC Portal, and Delays Portal to path to allow importing their apps
sys.path.append(str(BASE_DIR / 'TPM Portal'))
sys.path.append(str(BASE_DIR / 'CMC Portal'))
sys.path.append(str(BASE_DIR / 'Delays Portal'))
sys.path.append(str(BASE_DIR / 'EFMEA'))

# Security Settings (MUST match TPM Portal's SECRET_KEY for session sharing)
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-jspl-tpm-portal-secret-key-1029384756')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['172.17.18.43', '172.17.18.13', '127.0.0.1', 'localhost', '0.0.0.0', '*']
CSRF_TRUSTED_ORIGINS = [
    'https://*.loca.lt', 'http://*.loca.lt',
    'https://*.ngrok-free.app', 'http://*.ngrok-free.app',
    'https://*.ngrok-free.dev', 'http://*.ngrok-free.dev'
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    'corsheaders',
    'portal',
    'tpm',
    'cmc',
    'delays',
    'fmea',
    'capa',
    'Safety',
    'hod_kpi',
    'quality',
    'smed',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files in production
    'portal.middleware.StaticCacheMiddleware',  # Caches static files to optimize mobile WebView load times
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# CORS configuration
CORS_ALLOW_ALL_ORIGINS = True  # Allowed for mobile app development/access
CORS_ALLOW_CREDENTIALS = True


ROOT_URLCONF = 'main_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'portal' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'portal.context_processors.sidebar_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'main_portal.wsgi.application'

# Shared Database - SQLite by default, or PostgreSQL on Company Server if DB_NAME is set
if os.environ.get('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['DB_NAME'],
            'USER': os.environ.get('DB_USER', 'dept_db_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'TMPortal@4321'),
            'HOST': os.environ.get('DB_HOST', '172.17.0.20'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model mapped to existing tpm_user table
AUTH_USER_MODEL = 'tpm.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'portal.auth_backends.EmailBackend',
]

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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'portal' / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session Configuration (Must be aligned)
SESSION_COOKIE_AGE = 28800  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# Crispy Forms Configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Email Configuration (for local testing, prints to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'