from .settings import *
"""
This module overrides the default settings for running tests in a Django project.
It configures the following:
- Uses an in-memory SQLite database for faster test execution.
- Sets the static files storage to `StaticFilesStorage` to simplify static file handling during tests.
- Disables `DEBUG` mode to mimic production-like behavior during testing.
Importantly, this module inherits all settings from the base `settings` module and applies test-specific overrides.
"""

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
