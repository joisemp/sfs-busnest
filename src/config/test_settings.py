from .settings import *

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory database for faster tests
    }
}

# Static files configuration
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Other test-specific settings (if needed)
DEBUG = False
