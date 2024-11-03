cd src
set DJANGO_SETTINGS_MODULE=config.test_settings
python manage.py test
set DJANGO_SETTINGS_MODULE=config.settings
