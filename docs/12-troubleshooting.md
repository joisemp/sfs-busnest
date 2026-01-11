# Troubleshooting

Common issues and their solutions.

## Development Environment

### Docker Container Won't Start

**Issue**: Container exits immediately or fails to start

**Solutions**:

```bash
# Check logs
docker compose logs app

# Check all service status
docker compose ps

# Rebuild without cache
docker compose down
docker compose build --no-cache
docker compose up

# Check Docker resources
docker system df
docker system prune  # Clean up if needed
```

### Database Connection Errors

**Issue**: `could not connect to server` or `connection refused`

**Solutions**:

```bash
# Verify PostgreSQL is running
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres

# Restart PostgreSQL
docker compose restart postgres

# Verify environment variables
cat src/config/.env | grep DATABASE
```

### Port Already in Use

**Issue**: `port is already allocated`

**Solutions**:

```bash
# Windows - Find what's using port 7000
netstat -ano | findstr :7000

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :7000
kill -9 <PID>

# Or change port in docker-compose.yaml
ports:
  - "8000:8000"  # Use different port
```

### Celery Worker Not Processing Tasks

**Issue**: Tasks queue but never execute

**Solutions**:

```bash
# Check Celery worker logs
docker compose logs celery

# Restart Celery
docker compose restart celery

# Check Redis connection
docker compose logs redis

# Verify task is registered
docker exec -it sfs-busnest-celery-container celery -A config inspect registered
```

## Migrations

### Migration Conflicts

**Issue**: Multiple migration files for same app

**Solutions**:

```bash
# List migrations
docker exec -it sfs-busnest-container python manage.py showmigrations

# Fake merge migration if needed
docker exec -it sfs-busnest-container python manage.py migrate --fake <app> <migration>

# Or reset (WARNING: Deletes data)
docker compose down -v
docker compose up -d postgres
docker exec -it sfs-busnest-container python manage.py migrate
```

### "No such table" Error

**Issue**: Table doesn't exist in database

**Solutions**:

```bash
# Run migrations
docker exec -it sfs-busnest-container python manage.py migrate

# If still failing, check for pending migrations
docker exec -it sfs-busnest-container python manage.py showmigrations

# Make migrations if needed
docker exec -it sfs-busnest-container python manage.py makemigrations
docker exec -it sfs-busnest-container python manage.py migrate
```

## Application Errors

### 404 on Static Files

**Issue**: CSS/JS files return 404 in production

**Solutions**:

```bash
# Collect static files
docker exec -it sfs-busnest-container python manage.py collectstatic --noinput

# Check STATIC_ROOT in settings
# Verify WhiteNoise is enabled

# Check file exists
docker exec -it sfs-busnest-container ls -la /app/staticfiles/
```

### CSRF Verification Failed

**Issue**: Form submissions fail with CSRF error

**Solutions**:

```django
<!-- Ensure CSRF token in form -->
<form method="post">
    {% csrf_token %}
    <!-- form fields -->
</form>

<!-- For AJAX with HTMX -->
<form hx-post="{% url 'some:url' %}" hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    <!-- form fields -->
</form>
```

```python
# Verify CSRF middleware is enabled
# config/settings.py
MIDDLEWARE = [
    'django.middleware.csrf.CsrfViewMiddleware',  # Must be present
    # ...
]
```

### Permission Denied Errors

**Issue**: User cannot access page

**Solutions**:

1. Check user role:
```python
# In Django shell
docker exec -it sfs-busnest-container python manage.py shell

>>> from core.models import User
>>> user = User.objects.get(email='user@example.com')
>>> print(user.profile.role)
>>> print(user.profile.is_central_admin)
```

2. Verify access mixin on view:
```python
# Views must have appropriate mixin
class MyView(CentralAdminOnlyAccessMixin, LoginRequiredMixin, ListView):
    # ...
```

3. Check organisation assignment:
```python
>>> print(user.profile.org)  # Should not be None
```

### Trip Booking Count Incorrect

**Issue**: `booking_count` doesn't match actual tickets

**Solutions**:

```python
# Django shell
from services.models import Trip, Ticket

# Find affected trip
trip = Trip.objects.get(slug='trip-slug')

# Count actual tickets
actual_count = Ticket.objects.filter(
    Q(pickup_bus_record=trip.bus_record, pickup_route=trip.route, pickup_schedule=trip.schedule) |
    Q(drop_bus_record=trip.bus_record, drop_route=trip.route, drop_schedule=trip.schedule)
).count()

print(f"Current count: {trip.booking_count}")
print(f"Actual tickets: {actual_count}")

# Fix if needed
trip.booking_count = actual_count
trip.save()
```

## File Upload Issues

### Excel Processing Fails

**Issue**: Uploaded Excel file doesn't process

**Solutions**:

1. Check Flower for task status: http://localhost:5555
2. Check Celery logs:
```bash
docker compose logs celery | grep ERROR
```

3. Verify file format:
   - Must be .xlsx or .xls
   - Check required columns match expected format
   - No extra headers or merged cells

4. Check notification:
```python
from services.models import Notification
notifs = Notification.objects.filter(user=user).order_by('-created_at')[:5]
for n in notifs:
    print(f"{n.title}: {n.message}")
```

### File Upload Size Limit

**Issue**: Large files fail to upload

**Solutions**:

```python
# config/settings.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760

# Also check Django's FILE_UPLOAD_MAX_MEMORY_SIZE
```

## Frontend Issues

### HTMX Not Working

**Issue**: HTMX requests don't trigger

**Solutions**:

1. Check HTMX is loaded:
```django
<!-- In base.html -->
<script src="{% static 'utils/htmx/htmx.min.js' %}"></script>
```

2. Check network tab in browser DevTools
3. Verify URL is correct:
```django
<div hx-get="{% url 'namespace:view_name' %}" hx-trigger="load">
```

4. Check response is HTML:
```python
# View must return HTML, not JSON
def my_view(request):
    return render(request, 'partial.html', context)
```

### Bootstrap Modal Not Showing

**Issue**: Modal doesn't appear when triggered

**Solutions**:

```javascript
// Check for existing instance first
let modalElement = document.getElementById('myModal');
let modal = bootstrap.Modal.getInstance(modalElement);

if (!modal) {
    modal = new bootstrap.Modal(modalElement);
}

modal.show();

// Verify Bootstrap JS is loaded
console.log(typeof bootstrap);  // Should not be 'undefined'
```

### SCSS Not Compiling

**Issue**: SCSS changes don't appear

**Solutions**:

1. Check you're editing .scss not .css
2. Manually compile if needed:
```bash
# Install sass if not installed
npm install -g sass

# Compile SCSS
sass src/static/styles/central_admin/dashboard/style.scss src/static/styles/central_admin/dashboard/style.css
```

3. Clear browser cache (Ctrl+Shift+R)
4. Run collectstatic:
```bash
docker exec -it sfs-busnest-container python manage.py collectstatic --noinput
```

## Testing Issues

### Tests Fail with Database Errors

**Issue**: Tests can't create database

**Solutions**:

```bash
# Use test settings
cd src
DJANGO_SETTINGS_MODULE=config.test_settings python manage.py test

# Windows PowerShell
$env:DJANGO_SETTINGS_MODULE="config.test_settings"
python manage.py test
$env:DJANGO_SETTINGS_MODULE="config.settings"

# Or use script
./script/run_test.sh  # Linux/Mac
.\script\run_test.bat  # Windows
```

### Fixtures Won't Load

**Issue**: `loaddata` fails

**Solutions**:

```bash
# Check fixture file exists
ls -la src/fixtures/

# Try loading specific fixture
docker exec -it sfs-busnest-container python manage.py loaddata fixture_name.json

# Check for errors in fixture JSON
# Ensure all referenced foreign keys exist
```

## Performance Issues

### Slow Page Load

**Issue**: Pages take long to load

**Solutions**:

1. Check for N+1 queries:
```python
# Enable query logging in settings
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        }
    }
}

# Use select_related and prefetch_related
queryset = Ticket.objects.select_related(
    'pickup_route',
    'drop_route'
).prefetch_related(
    'payments'
)
```

2. Check database indexes:
```python
# Ensure slug fields have db_index=True
slug = models.SlugField(unique=True, db_index=True)
```

3. Use Django Debug Toolbar (development):
```python
# config/settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### Celery Tasks Slow

**Issue**: Background tasks take too long

**Solutions**:

1. Check Flower: http://localhost:5555
2. Monitor task execution:
```python
from celery import current_task

@shared_task
def my_task():
    current_task.update_state(state='PROGRESS', meta={'current': 50, 'total': 100})
```

3. Optimize queries in tasks:
```python
# Use bulk operations
Ticket.objects.bulk_create([...])
Ticket.objects.filter(...).update(status='confirmed')
```

## Production Issues

### Email Not Sending

**Issue**: Emails don't send in production

**Solutions**:

```python
# Check email backend
# config/settings.py
if ENVIRONMENT == 'production':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.mailjet.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get('MAILJET_API_KEY')
    EMAIL_HOST_PASSWORD = os.environ.get('MAILJET_SECRET_KEY')

# Test email
docker exec -it sfs-busnest-container python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
```

### Static Files Missing in Production

**Issue**: CSS/JS not loading

**Solutions**:

```python
# Ensure static files configured
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Collect static files
python manage.py collectstatic --noinput

# Check WhiteNoise middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # After SecurityMiddleware
    # ...
]
```

### Database Connection Pool Exhausted

**Issue**: "too many connections" error

**Solutions**:

```python
# Configure connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 60,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Or use pgbouncer for connection pooling
```

## Common Error Messages

### "Organisation matching query does not exist"

**Cause**: User profile doesn't have organisation assigned

**Solution**:
```python
# Assign organisation to user
user.profile.org = Organisation.objects.get(id=1)
user.profile.save()
```

### "This field is required"

**Cause**: Form validation failing

**Solution**:
1. Check form is receiving all required data
2. Verify field is not in `exclude` list
3. Check if field should be optional:
```python
field = models.CharField(max_length=100, blank=True, null=True)
```

### "Unique constraint failed"

**Cause**: Trying to create duplicate slug or unique field

**Solution**:
```python
# Use get_or_create
obj, created = Model.objects.get_or_create(
    slug=slug,
    defaults={'name': name, 'org': org}
)

# Or catch exception
try:
    obj.save()
except IntegrityError:
    # Handle duplicate
    pass
```

## Debug Tips

### Enable Debug Toolbar

```bash
pip install django-debug-toolbar

# config/settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
```

### Django Shell Tips

```python
# Start shell
docker exec -it sfs-busnest-container python manage.py shell

# Useful commands
from services.models import *
from core.models import User

# Count models
print(f"Users: {User.objects.count()}")
print(f"Tickets: {Ticket.objects.count()}")

# Check last created
latest = Ticket.objects.order_by('-created_at').first()
print(latest.__dict__)

# Raw SQL
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT COUNT(*) FROM services_ticket")
print(cursor.fetchone())
```

### Logging

```python
# Add to views
import logging
logger = logging.getLogger(__name__)

def my_view(request):
    logger.debug(f"User: {request.user}")
    logger.info(f"Accessing view: {request.path}")
    logger.error(f"Error occurred: {error}")
```

## Getting Help

### Internal Resources
1. Team documentation (this guide)
2. Internal issue/ticket system
3. Team members and senior developers
4. Django documentation: https://docs.djangoproject.com/

### Creating Bug Reports

Include:
1. Error message (full traceback)
2. Steps to reproduce
3. Expected vs actual behavior
4. Environment (development/production)
5. Recent changes to code
6. Assign to appropriate team member

### Useful Commands

```bash
# Check Django version
docker exec -it sfs-busnest-container python -c "import django; print(django.get_version())"

# Check installed packages
docker exec -it sfs-busnest-container pip list

# Database shell
docker exec -it postgres-container psql -U postgres -d postgres

# Redis CLI
docker exec -it redis-container redis-cli
```

## Emergency Procedures

### Reset Database (Development Only)

```bash
# WARNING: Deletes all data
docker compose down -v
docker compose up -d postgres
docker exec -it sfs-busnest-container python manage.py migrate
docker exec -it sfs-busnest-container python manage.py createsuperuser
```

### Clear Cache

```bash
# Redis CLI
docker exec -it redis-container redis-cli FLUSHALL

# Django
docker exec -it sfs-busnest-container python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### Rollback Migration

```bash
# Rollback to specific migration
docker exec -it sfs-busnest-container python manage.py migrate services 0005_previous_migration

# Check current state
docker exec -it sfs-busnest-container python manage.py showmigrations
```
