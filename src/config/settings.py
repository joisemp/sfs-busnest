import os
from pathlib import Path
from environ import Env

"""
Django settings for the project.
This module contains the configuration for the Django project, including
settings for development and production environments. It uses environment
variables for sensitive information and supports features like Celery, 
DigitalOcean Spaces, and email configuration.
Attributes:
    ENVIRONMENT (str): The current environment ('development' or 'production').
    TIME_ZONE (str): The timezone for the project, set to 'Asia/Kolkata'.
    USE_TZ (bool): Whether to use timezone-aware datetimes.
    BASE_DIR (Path): The base directory of the project.
    LOGIN_URL (str): The URL for the login page.
    AUTH_USER_MODEL (str): The custom user model for the project.
    DEBUG (bool): Debug mode status, determined by the environment.
    SECRET_KEY (str): The secret key for the project.
    ALLOWED_HOSTS (list): List of allowed hosts for the project.
    SITE_URL (str): The base URL of the site.
    SESSION_COOKIE_AGE (int): The age of session cookies in seconds.
    INSTALLED_APPS (list): List of installed Django apps.
    MIDDLEWARE (list): List of middleware for the project.
    ALLOW_USER_REGISTRATION (bool): Whether user registration is allowed.
    MAINTENANCE_MODE (bool): Whether the site is in maintenance mode.
    ROOT_URLCONF (str): The root URL configuration module.
    TEMPLATES (list): Configuration for Django templates.
    WSGI_APPLICATION (str): The WSGI application module.
    DATABASES (dict): Database configuration based on the environment.
    CELERY_BROKER_URL (str): The URL for the Celery broker.
    CELERY_RESULT_BACKEND (str): The backend for storing Celery task results.
    CELERY_RESULT_EXTENDED (bool): Whether to use extended Celery results.
    CSRF_TRUSTED_ORIGINS (list): List of trusted origins for CSRF protection.
    AUTH_PASSWORD_VALIDATORS (list): List of password validation rules.
    LANGUAGE_CODE (str): The default language code.
    STATIC_URL (str): The URL for serving static files.
    STATICFILES_DIRS (list): List of directories for static files.
    STATIC_ROOT (str): The directory for collecting static files.
    MEDIA_URL (str): The URL for serving media files.
    MEDIA_ROOT (str): The directory for storing media files.
    AWS_ACCESS_KEY_ID (str): AWS access key ID for DigitalOcean Spaces.
    AWS_SECRET_ACCESS_KEY (str): AWS secret access key for DigitalOcean Spaces.
    AWS_STORAGE_BUCKET_NAME (str): AWS storage bucket name.
    AWS_S3_ENDPOINT_URL (str): AWS S3 endpoint URL.
    AWS_S3_CUSTOM_DOMAIN (str): Custom domain for AWS S3.
    AWS_S3_OBJECT_PARAMETERS (dict): Parameters for AWS S3 objects.
    EMAIL_BACKEND (str): Email backend configuration.
    EMAIL_HOST (str): Email host for SMTP.
    EMAIL_PORT (int): Email port for SMTP.
    EMAIL_USE_TLS (bool): Whether to use TLS for email.
    EMAIL_HOST_USER (str): Email host username.
    EMAIL_HOST_PASSWORD (str): Email host password.
    DEFAULT_FROM_EMAIL (str): Default email address for outgoing emails.
    LOGGING (dict): Logging configuration for the project.
"""

env = Env()
Env.read_env()

ENVIRONMENT = env('ENVIRONMENT', default="development")

# Set the timezone to IST
TIME_ZONE = 'Asia/Kolkata'

# Ensure that Django uses timezone-aware datetimes
USE_TZ = True

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

LOGIN_URL = '/core/login'

AUTH_USER_MODEL = 'core.User'

if ENVIRONMENT == 'development':
    DEBUG = True
else:
    DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default="secret_key")


ALLOWED_HOSTS = env('ALLOWED_HOSTS', default='example.com').split(',')

SITE_URL = env('SITE_URL', default='http://localhost:8000/')

SESSION_COOKIE_AGE = 60 * 60 * 24  # 1 day

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_results',
    'django_celery_beat',
    'core',
    'services'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ALLOW_USER_REGISTRATION = True

MAINTENANCE_MODE = False

MIDDLEWARE += [
    'config.middleware.maintenance_mode.MaintenanceModeMiddleware',
]


ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.priority_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

if ENVIRONMENT == 'development':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'postgres',
            'USER': 'postgres',
            'PASSWORD': 'postgres',
            'HOST': 'postgres',
            'PORT': 5432,
        }
    }
    
    CELERY_BROKER_URL = 'redis://redis:6379/0'
else:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(env('DATABASE_URL', default='postgresql://'))
    }
    CELERY_BROKER_URL = env('REDIS_URL', default='redis://')


CELERY_RESULT_BACKEND = 'django-db'
CELERY_RESULT_EXTENDED = True


CSRF_TRUSTED_ORIGINS = [
    url.strip() for url in env('CSRF_TRUSTED_ORIGINS', default='https://example.com').split(',')
]


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


if ENVIRONMENT == 'development':
    STATIC_URL = '/static/'
    STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
else:
    # DigitalOcean Spaces Configuration
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default="aws_access_key")
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default="aws_secret_access_key")
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default="aws_storage_bucket_name")
    AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default="aws_s3_endpoint_url")
    AWS_S3_CUSTOM_DOMAIN = f"{env('AWS_S3_CUSTOM_DOMAIN', default="aws_s3_custom_domain")}/{AWS_STORAGE_BUCKET_NAME}"

    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }

    # Static Files
    STATIC_URL = f"{AWS_S3_CUSTOM_DOMAIN}/{AWS_STORAGE_BUCKET_NAME}/static/"
    STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, "static"),
    ]

    # Media Files
    MEDIA_URL = f"{AWS_S3_CUSTOM_DOMAIN}/{AWS_STORAGE_BUCKET_NAME}/media/"
    STATICFILES_STORAGE = "config.storages.StaticStorage"
    DEFAULT_FILE_STORAGE = "config.storages.MediaStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# email settings
if ENVIRONMENT == 'development':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = env('EMAIL_HOST', default='in-v3.mailjet.com')
    EMAIL_PORT = env.int('EMAIL_PORT', default=587)
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {name} {funcName} {lineno} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': 'debug.log',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'core': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'services': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    }

