import os
"""
This module configures the Celery application for the Django project.
The Celery application is initialized with the following steps:
1. Sets the default Django settings module to 'config.settings'.
2. Creates a Celery application instance named 'config'.
3. Configures the Celery application using Django's settings, with the namespace 'CELERY'.
4. Automatically discovers tasks from all installed Django apps.
Attributes:
    celery_app (Celery): The Celery application instance used for task management.
Usage:
    Import `celery_app` in other modules to define or execute Celery tasks.
"""
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

celery_app = Celery('config')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()