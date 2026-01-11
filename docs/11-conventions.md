# Conventions & Best Practices

This document outlines coding conventions, patterns, and best practices for the SFS BusNest project.

## General Python Conventions

### Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 120 characters
- Use snake_case for functions and variables
- Use PascalCase for class names

### Imports
```python
# Standard library imports
import os
import re
from datetime import datetime

# Django imports
from django.db import models
from django.views.generic import ListView

# Third-party imports
from celery import shared_task

# Local imports
from services.models import Route, Stop
from config.utils import generate_unique_slug
```

## Django-Specific Conventions

### 1. Model Conventions

#### Always Include These Fields
```python
class MyModel(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE)  # Multi-tenancy
    slug = models.SlugField(unique=True, db_index=True)  # URL-friendly identifier
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### Auto-Generate Slugs
```python
def save(self, *args, **kwargs):
    if not self.slug:
        self.slug = generate_unique_slug(self.__class__, self.name)
    super().save(*args, **kwargs)
```

#### Use Soft Deletes
```python
# Instead of model.delete()
model.is_available = False
model.status = 'cancelled'
model.save()
```

#### Model Documentation
```python
class Trip(models.Model):
    """
    Represents a specific trip (route + schedule + bus).
    
    A trip is a unique combination of a bus record, route, and schedule
    within a registration. The booking_count tracks current seat allocation.
    
    Attributes:
        registration: The registration this trip belongs to
        bus_record: The bus assigned to this trip
        route: The route this trip follows
        schedule: The time schedule for this trip
        booking_count: Current number of bookings (updated automatically)
    """
```

### 2. View Conventions

#### Use Class-Based Views
```python
# Preferred
class MyListView(CentralAdminOnlyAccessMixin, LoginRequiredMixin, ListView):
    model = MyModel
    template_name = 'central_admin/my_list.html'
    context_object_name = 'items'
    
    def get_queryset(self):
        return super().get_queryset().filter(org=self.request.user.profile.org)

# Avoid function-based views for consistency
```

#### Always Use Access Mixins
```python
# CORRECT
class MyView(CentralAdminOnlyAccessMixin, LoginRequiredMixin, TemplateView):
    pass

# WRONG - No access control
class MyView(TemplateView):
    pass
```

#### Filter by Organisation
```python
def get_queryset(self):
    return super().get_queryset().filter(
        org=self.request.user.profile.org
    )
```

#### Use select_related and prefetch_related
```python
# Optimize database queries
def get_queryset(self):
    return Ticket.objects.filter(
        org=self.request.user.profile.org
    ).select_related(
        'pickup_route',
        'drop_route',
        'institution'
    ).prefetch_related(
        'payments'
    )
```

### 3. Form Conventions

#### Organize by Role
```
services/forms/
├── central_admin.py
├── institution_admin.py
├── drivers.py
└── students.py
```

#### Use Model Forms
```python
class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['student_id', 'student_name', 'pickup_route', 'drop_route']
        widgets = {
            'student_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize based on user
        if user:
            self.fields['pickup_route'].queryset = Route.objects.filter(
                org=user.profile.org
            )
```

#### Bootstrap Classes
```python
# Always add Bootstrap classes for consistency
widgets = {
    'name': forms.TextInput(attrs={'class': 'form-control'}),
    'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
}
```

### 4. URL Conventions

#### Use Namespaces
```python
# services/urls/central_admin.py
app_name = 'central_admin'

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('routes/<slug:slug>/', views.RouteDetailView.as_view(), name='route_detail'),
]
```

#### Use Slugs in URLs
```python
# CORRECT
path('routes/<slug:slug>/', views.RouteDetailView.as_view(), name='route_detail')

# AVOID
path('routes/<int:pk>/', views.RouteDetailView.as_view(), name='route_detail')
```

#### RESTful Patterns
```python
path('routes/', views.RouteListView.as_view(), name='route_list')  # List
path('routes/create/', views.RouteCreateView.as_view(), name='route_create')  # Create
path('routes/<slug:slug>/', views.RouteDetailView.as_view(), name='route_detail')  # Detail
path('routes/<slug:slug>/update/', views.RouteUpdateView.as_view(), name='route_update')  # Update
path('routes/<slug:slug>/delete/', views.RouteDeleteView.as_view(), name='route_delete')  # Delete
```

### 5. Template Conventions

#### Extend Base Templates
```django
{% extends 'base.html' %}

{% block title %}My Page{% endblock %}

{% block content %}
<div class="container">
    <!-- Content here -->
</div>
{% endblock %}
```

#### Use Template Tags
```django
{% load static %}
{% load services_tags %}  # Custom template tags

<link rel="stylesheet" href="{% static 'styles/central_admin/dashboard/style.css' %}">
```

#### HTMX Integration
```django
<!-- Dynamic loading -->
<select hx-get="{% url 'central_admin:student_group_filter' %}" 
        hx-target="#student-group-container" 
        hx-trigger="change">
</select>

<!-- Form submission -->
<form hx-post="{% url 'central_admin:create_stop' %}" 
      hx-target="#stops-list"
      hx-swap="beforeend">
    {% csrf_token %}
    <!-- Form fields -->
</form>
```

## Frontend Conventions

### 1. SCSS Organization

#### Modular Structure
```
styles/
├── base/
│   ├── _colors.scss       # Color variables
│   ├── _typography.scss   # Font styles
│   └── _buttons.scss      # Button styles
└── central_admin/
    └── dashboard/
        ├── style.scss     # EDIT THIS
        └── style.css      # AUTO-GENERATED - DO NOT EDIT
```

#### Use Variables
```scss
// Import base styles
@use '../../base/colors' as *;

// Use color variables
.card {
    background-color: $indigo-600;
    color: $gray-50;
}

// Use SASS 2.0 functions
.button {
    background-color: color.scale($indigo-600, $lightness: -10%);
}
```

#### Never Edit CSS Directly
```scss
// CORRECT: Edit .scss files
// src/static/styles/central_admin/dashboard/style.scss

// WRONG: Never edit .css files
// src/static/styles/central_admin/dashboard/style.css (auto-generated)
```

### 2. JavaScript Conventions

#### Vanilla JS Only
```javascript
// CORRECT - Vanilla JS
document.getElementById('myButton').addEventListener('click', function() {
    // Handle click
});

// AVOID - No jQuery, React, Vue, etc.
$('#myButton').click(function() { ... });
```

#### Use Bootstrap Components
```javascript
// Initialize Bootstrap modal
const modal = new bootstrap.Modal(document.getElementById('myModal'));
modal.show();

// Initialize Bootstrap tooltip
const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});
```

#### Check for Existing Instances
```javascript
// CORRECT - Check before creating
let modal = bootstrap.Modal.getInstance(modalElement);
if (!modal) {
    modal = new bootstrap.Modal(modalElement);
}
modal.show();

// WRONG - Memory leak
const modal = new bootstrap.Modal(modalElement);  // Creates duplicate
```

## Celery Task Conventions

### Task Organization
```python
# services/tasks.py
from celery import shared_task
from services.models import Notification

@shared_task
def process_uploaded_route_excel(route_file_id, user_id):
    """
    Process uploaded route Excel file asynchronously.
    
    Creates routes and stops from Excel data and updates notification.
    
    Args:
        route_file_id: ID of the RouteFile instance
        user_id: ID of the user who uploaded the file
    """
    # Create initial notification
    notification = Notification.objects.create(
        user_id=user_id,
        title="Processing Route File",
        message="Your route file is being processed...",
        notification_type='info'
    )
    
    try:
        # Process file
        # ...
        
        # Update notification on success
        notification.message = f"Successfully created {route_count} routes"
        notification.notification_type = 'success'
        notification.save()
    except Exception as e:
        # Update notification on error
        notification.message = f"Error: {str(e)}"
        notification.notification_type = 'error'
        notification.save()
        raise
```

### Always Create Notifications
```python
# Create notification at start
notification = Notification.objects.create(...)

# Update notification at end
notification.status = 'completed'
notification.save()
```

## Naming Conventions

### Models
```python
class BusRecord(models.Model):  # Singular, PascalCase
    pass
```

### Views
```python
class RouteListView(ListView):  # Descriptive + View suffix
    pass
```

### Forms
```python
class RouteCreateForm(ModelForm):  # Descriptive + Form suffix
    pass
```

### URLs
```python
path('routes/', ..., name='route_list')  # snake_case, descriptive
```

### Templates
```
route_list.html  # snake_case, matches view name
route_form.html
```

### Functions
```python
def generate_unique_slug(model_class, base_text):  # snake_case, descriptive
    pass
```

## Error Handling

### Use Try-Except Appropriately
```python
try:
    ticket = Ticket.objects.get(slug=slug, org=org)
except Ticket.DoesNotExist:
    messages.error(request, 'Ticket not found')
    return redirect('students:dashboard')
```

### Log Errors
```python
import logging

logger = logging.getLogger(__name__)

try:
    # Some operation
    pass
except Exception as e:
    logger.error(f"Error in operation: {str(e)}", exc_info=True)
    raise
```

### User-Friendly Messages
```python
# CORRECT
messages.error(request, 'Unable to create ticket. Please try again.')

# WRONG
messages.error(request, 'IntegrityError: duplicate key value violates...')
```

## Database Conventions

### Use Transactions
```python
from django.db import transaction

@transaction.atomic
def transfer_stop(stop, new_route):
    # All operations succeed or all fail
    stop.route = new_route
    stop.save()
    
    # Update all tickets
    tickets = Ticket.objects.filter(pickup_stop=stop)
    for ticket in tickets:
        ticket.pickup_route = new_route
        ticket.save()
```

### Avoid N+1 Queries
```python
# WRONG - N+1 queries
for ticket in tickets:
    print(ticket.pickup_route.name)  # Database query per ticket

# CORRECT - Single query
tickets = tickets.select_related('pickup_route')
for ticket in tickets:
    print(ticket.pickup_route.name)  # No additional query
```

### Update Counts Correctly
```python
# When creating ticket
ticket.save()
trip.booking_count = F('booking_count') + 1
trip.save()
trip.refresh_from_db()  # Get updated value

# When deleting ticket (handled by signal)
@receiver(post_delete, sender=Ticket)
def update_trip_booking_count(sender, instance, **kwargs):
    # Automatically decrements count
```

## Security Best Practices

### 1. Always Validate User Input
```python
def clean_student_id(self):
    student_id = self.cleaned_data['student_id']
    if not student_id.isalnum():
        raise ValidationError('Student ID must be alphanumeric')
    return student_id
```

### 2. Use CSRF Tokens
```django
<form method="post">
    {% csrf_token %}
    <!-- Form fields -->
</form>
```

### 3. Validate File Uploads
```python
from config.validators import validate_excel_file

file = models.FileField(
    upload_to=rename_uploaded_file,
    validators=[validate_excel_file]  # Check file type and size
)
```

### 4. Log User Actions
```python
from services.models.utils import log_user_activity

log_user_activity(
    user=request.user,
    action='Route Created',
    description=f'Created route: {route.name}',
    ip_address=request.META.get('REMOTE_ADDR')
)
```

## Testing Conventions

### Organize Tests
```
services/test/
├── __init__.py
├── test_models.py
├── test_views.py
├── test_forms.py
└── test_tasks.py
```

### Test Model Validation
```python
def test_slug_auto_generation(self):
    route = Route.objects.create(
        name="Test Route",
        registration=self.registration,
        org=self.org
    )
    self.assertIsNotNone(route.slug)
    self.assertTrue(route.slug.startswith('test-route'))
```

### Use Test Settings
```bash
cd src
DJANGO_SETTINGS_MODULE=config.test_settings python manage.py test
```

## Documentation Conventions

### Docstrings
```python
def move_stop_and_update_tickets(stop, new_route, user):
    """
    Transfer stop to new route and update all associated tickets.
    
    This function performs an atomic transaction to:
    1. Move the stop to the new route
    2. Update all tickets referencing this stop
    3. Update trip booking counts
    4. Log the activity
    
    Args:
        stop (Stop): The stop to transfer
        new_route (Route): The destination route
        user (User): The user performing the action
    
    Returns:
        tuple: (success: bool, message: str, updated_count: int)
    
    Raises:
        ValidationError: If routes are in different registrations
    """
```

### Code Comments
```python
# GOOD - Explains WHY
# Transfer type determines which bus records to update
# Pickup only = update pickup_bus_record only
transfer_type = determine_transfer_type(old_route, new_route)

# BAD - States the obvious
# Loop through tickets
for ticket in tickets:
```

## Git Conventions

### Branch Naming
```bash
feature/stop-transfer-ui
bugfix/ticket-count-update
hotfix/security-patch
```

### Commit Messages
```
feat: Add stop transfer drag-and-drop interface
fix: Correct trip booking count on ticket deletion
docs: Update architecture documentation
refactor: Reorganize models into separate files
test: Add tests for stop transfer utility
```

### Before Committing
```bash
# Run tests
cd src && DJANGO_SETTINGS_MODULE=config.test_settings python manage.py test

# Check for migrations
docker exec -it sfs-busnest-container python manage.py makemigrations --check

# Review changes
git diff
```

## Performance Best Practices

### 1. Use Indexes
```python
slug = models.SlugField(unique=True, db_index=True)  # Index for fast lookups
```

### 2. Cache Expensive Operations
```python
from django.core.cache import cache

def get_dashboard_stats(org):
    cache_key = f'dashboard_stats_{org.id}'
    stats = cache.get(cache_key)
    
    if not stats:
        stats = calculate_stats(org)
        cache.set(cache_key, stats, 300)  # 5 minutes
    
    return stats
```

### 3. Use Background Tasks
```python
# Don't process in request/response cycle
@shared_task
def generate_large_report(user_id, params):
    # Long-running operation
    pass
```

## Common Gotchas

### 1. Trip Booking Count
```python
# WRONG - Direct assignment
trip.booking_count += 1

# CORRECT - Use F() expression
from django.db.models import F
trip.booking_count = F('booking_count') + 1
trip.save()
```

### 2. Role System
```python
# CORRECT - Use role field
if user.profile.role == UserProfile.CENTRAL_ADMIN:

# ALSO CORRECT - Use property
if user.profile.is_central_admin:

# WRONG - Check non-existent boolean
if user.profile.is_admin:  # This doesn't exist
```

### 3. Model Imports
```python
# CORRECT - Import from __init__.py
from services.models import Route, Stop, Trip

# WRONG - Import from individual files
from services.models.routes import Route  # Avoid
```

## Next Steps

- **Backend Development**: [Backend Development](./06-backend-development.md)
- **Frontend Development**: [Frontend Development](./07-frontend-development.md)
- **Testing**: [Testing Guide](./09-testing.md)
