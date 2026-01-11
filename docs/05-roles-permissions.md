# User Roles & Permissions

This document details the role-based access control system in SFS BusNest.

## Overview

SFS BusNest implements a role-based access control (RBAC) system with four distinct user roles. Each role has specific permissions and accesses different parts of the application.

## User Role Model

### Role Field

**Location**: `core/models.py` - `UserProfile`

```python
class UserProfile(models.Model):
    # Role constants
    CENTRAL_ADMIN = 'central_admin'
    INSTITUTION_ADMIN = 'institution_admin'
    DRIVER = 'driver'
    STUDENT = 'student'
    
    ROLE_CHOICES = [
        (CENTRAL_ADMIN, _('Central Admin')),
        (INSTITUTION_ADMIN, _('Institution Admin')),
        (DRIVER, _('Driver')),
        (STUDENT, _('Student')),
    ]
    
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default=STUDENT
    )
```

### Role Properties

For backward compatibility, UserProfile provides boolean properties:

```python
@property
def is_central_admin(self):
    return self.role == self.CENTRAL_ADMIN

@property
def is_institution_admin(self):
    return self.role == self.INSTITUTION_ADMIN

@property
def is_driver(self):
    return self.role == self.DRIVER

@property
def is_student(self):
    return self.role == self.STUDENT
```

## Roles & Permissions

### 1. Central Admin

**Access Level**: Full system access

**Responsibilities**:
- Manage all organizations and institutions
- Upload and manage bus fleet
- Create and manage routes
- Set up registrations and schedules
- Upload receipts for students
- Generate trips (route + schedule + bus)
- View all bookings and tickets
- Handle bus reservation requests
- Export reports and analytics
- Manage all system users

**URL Namespace**: `/central_admin/`

**Dashboard Features**:
- Total students count
- Total buses count
- Active registrations
- Recent activities
- System-wide statistics

**Key Permissions**:
```python
- Create/Edit/Delete: Organisation, Institution
- Create/Edit/Delete: Bus, Route, Stop
- Create/Edit/Delete: Registration, Schedule, ScheduleGroup
- Upload: BusFile, RouteFile, ReceiptFile
- Create/Edit: BusRecord, Trip
- View/Export: All Tickets
- Manage: BusReservationRequest
- Manage: All Users
```

**Access Control Mixin**:
```python
from config.mixins.access_mixin import CentralAdminOnlyAccessMixin

class SomeView(CentralAdminOnlyAccessMixin, LoginRequiredMixin, ListView):
    # Only central admins can access
    pass
```

---

### 2. Institution Admin

**Access Level**: Institution-scoped access

**Responsibilities**:
- View their institution's data
- Manage student groups
- Create bus reservation requests
- View institution's student bookings
- Generate institution-specific reports
- Cannot access other institutions' data

**URL Namespace**: `/institution_admin/`

**Dashboard Features**:
- Institution's student count
- Active bookings for institution
- Pending reservation requests
- Institution-specific stats

**Key Permissions**:
```python
- View: Own Institution only
- Create/Edit: StudentGroup (own institution)
- Create: BusReservationRequest
- View: BusReservationRequest (own institution)
- View: Tickets (own institution students)
- View: Routes, Schedules (registration-level)
```

**Data Filtering**:
```python
# Always filter by institution
tickets = Ticket.objects.filter(
    org=request.user.profile.org,
    institution=request.user.profile.institution
)
```

**Access Control Mixin**:
```python
from config.mixins.access_mixin import InstitutionAdminOnlyAccessMixin

class SomeView(InstitutionAdminOnlyAccessMixin, LoginRequiredMixin, ListView):
    # Only institution admins can access
    pass
```

---

### 3. Driver

**Access Level**: Limited to assigned bus operations

**Responsibilities**:
- View assigned trips and schedules
- Log refueling records for assigned bus
- Track odometer readings
- View route and stop information
- Access only during active registration

**URL Namespace**: `/drivers/`

**Dashboard Features**:
- Assigned bus information
- Today's trips
- Recent refueling records
- Quick add refueling button

**Key Permissions**:
```python
- View: Assigned BusRecord (active registration)
- View: Trips for assigned bus
- Create/Edit: RefuelingRecord (own bus only)
- View: Routes, Stops (for assigned trips)
```

**Access Pattern**:
```python
# Only one active registration
active_registration = Registration.objects.filter(
    org=profile.org,
    is_active=True
).first()

# Driver's assigned bus in active registration
bus_record = BusRecord.objects.filter(
    registration=active_registration,
    driver=request.user,
    org=profile.org
).first()

# Only access assigned bus data
refueling_records = RefuelingRecord.objects.filter(
    bus=bus_record.bus,
    org=profile.org
)
```

**Access Control Mixin**:
```python
from config.mixins.access_mixin import DriverOnlyAccessMixin

class SomeView(DriverOnlyAccessMixin, LoginRequiredMixin, ListView):
    # Only drivers can access
    pass
```

**Key Features**:
- **Refueling Management**: Create and update refueling records
- **Trip Visibility**: View assigned routes and schedules
- **Bus Information**: Access bus capacity and details

---

### 4. Student

**Access Level**: Read-only, personal data only

**Responsibilities**:
- Access registration with unique code
- View available routes and schedules
- Book bus seats (if receipt is valid)
- View own tickets
- Download student pass
- View assigned bus and schedule details

**URL Namespace**: `/students/`

**Dashboard Features**:
- Active tickets
- Booking history
- Bus schedules
- Download pass option

**Key Permissions**:
```python
- View: Registration (via code)
- View: Routes, Stops, Schedules (active registration)
- Create: Ticket (if valid receipt exists)
- View: Own Tickets only
- Download: Own StudentPassFile
```

**Booking Validation**:
```python
# Student needs valid receipt
receipt = Receipt.objects.filter(
    registration=registration,
    student_id=student_id,
    is_expired=False,
    org=registration.org
).first()

if not receipt:
    raise ValidationError("No valid receipt found")

# Check capacity
if trip.booking_count >= trip.bus_record.bus.capacity:
    raise ValidationError("Bus is full")

# Create ticket
ticket = Ticket.objects.create(...)
trip.booking_count += 1
trip.save()
```

**Access Control Mixin**:
```python
from config.mixins.access_mixin import StudentOnlyAccessMixin

class SomeView(StudentOnlyAccessMixin, LoginRequiredMixin, ListView):
    # Only students can access
    pass
```

---

## Access Control Implementation

### 1. Access Mixins

**Location**: `config/mixins/access_mixin.py`

```python
class CentralAdminOnlyAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.profile.is_central_admin:
            return redirect('core:login')
        return super().dispatch(request, *args, **kwargs)

class InstitutionAdminOnlyAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.profile.is_institution_admin:
            return redirect('core:login')
        return super().dispatch(request, *args, **kwargs)

class DriverOnlyAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.profile.is_driver:
            return redirect('core:login')
        return super().dispatch(request, *args, **kwargs)

class StudentOnlyAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.profile.is_student:
            return redirect('core:login')
        return super().dispatch(request, *args, **kwargs)
```

### 2. View Protection

All views must use appropriate mixins:

```python
# Central Admin View
class ManageBusesView(CentralAdminOnlyAccessMixin, LoginRequiredMixin, ListView):
    model = Bus
    
    def get_queryset(self):
        return Bus.objects.filter(org=self.request.user.profile.org)

# Institution Admin View
class InstitutionDashboardView(InstitutionAdminOnlyAccessMixin, LoginRequiredMixin, TemplateView):
    template_name = 'institution_admin/dashboard.html'

# Driver View
class DriverRefuelingListView(DriverOnlyAccessMixin, LoginRequiredMixin, ListView):
    model = RefuelingRecord

# Student View
class StudentTicketsView(StudentOnlyAccessMixin, LoginRequiredMixin, ListView):
    model = Ticket
    
    def get_queryset(self):
        return Ticket.objects.filter(
            student_id=self.request.user.profile.student_id,
            org=self.request.user.profile.org
        )
```

### 3. URL Namespaces

Each role has a separate URL namespace:

```python
# config/urls.py
urlpatterns = [
    path('central_admin/', include('services.urls.central_admin')),
    path('institution_admin/', include('services.urls.institution_admin')),
    path('drivers/', include('services.urls.drivers')),
    path('students/', include('services.urls.students')),
]
```

### 4. Template Access Control

Templates check user roles:

```django
{% if request.user.profile.is_central_admin %}
    <a href="{% url 'central_admin:dashboard' %}">Admin Dashboard</a>
{% elif request.user.profile.is_institution_admin %}
    <a href="{% url 'institution_admin:dashboard' %}">Institution Dashboard</a>
{% elif request.user.profile.is_driver %}
    <a href="{% url 'drivers:dashboard' %}">Driver Dashboard</a>
{% elif request.user.profile.is_student %}
    <a href="{% url 'students:dashboard' %}">Student Dashboard</a>
{% endif %}
```

---

## Multi-Tenancy

All data access is scoped by organization:

```python
# Always filter by org
queryset = Model.objects.filter(org=request.user.profile.org)

# Enforce in view
def get_queryset(self):
    return super().get_queryset().filter(
        org=self.request.user.profile.org
    )
```

**Key Points**:
- Every model has `org` ForeignKey
- All queries must filter by `org`
- Users cannot access data from other organizations
- Even central admins are organization-scoped

---

## Permission Matrix

| Resource | Central Admin | Institution Admin | Driver | Student |
|----------|--------------|-------------------|--------|---------|
| Organisation | Create, Edit, Delete | View (own) | View (own) | View (own) |
| Institution | Create, Edit, Delete | View (own) | View (own) | View (own) |
| Bus | Create, Edit, Delete | View | View (assigned) | View |
| Route | Create, Edit, Delete | View | View (assigned) | View |
| Stop | Create, Edit, Delete | View | View (assigned) | View |
| Registration | Create, Edit, Delete | View | View (active) | View (via code) |
| Schedule | Create, Edit, Delete | View | View (assigned) | View |
| BusRecord | Create, Edit, Delete | View | View (assigned) | View |
| Trip | Create, Edit, Delete | View | View (assigned) | View |
| Ticket | View All, Export | View (own inst) | - | View (own), Create |
| Receipt | Upload, Create | - | - | - |
| RefuelingRecord | View All | - | Create, Edit (own) | - |
| BusReservationRequest | View, Approve | Create, View (own) | - | - |
| UserActivity | View All | - | - | - |
| Notification | View (own) | View (own) | View (own) | View (own) |

---

## Role Assignment

### Creating Users

```python
# Create user
user = User.objects.create_user(
    email='user@example.com',
    password='password123'
)

# Create profile with role
profile = UserProfile.objects.create(
    user=user,
    org=organisation,
    first_name='John',
    last_name='Doe',
    role=UserProfile.CENTRAL_ADMIN  # or INSTITUTION_ADMIN, DRIVER, STUDENT
)
```

### Changing Roles

```python
# Update role
profile = user.profile
profile.role = UserProfile.DRIVER
profile.save()
```

### Checking Roles

```python
# In views
if request.user.profile.is_central_admin:
    # Central admin logic

# In templates
{% if request.user.profile.is_driver %}
    <!-- Driver-specific content -->
{% endif %}
```

---

## Security Considerations

### 1. Always Use Mixins
Never rely on template-level checks alone. Always protect views with access mixins.

### 2. Filter by Organisation
Always filter queries by `org=request.user.profile.org` to enforce multi-tenancy.

### 3. Validate Ownership
For resources with additional ownership (e.g., tickets), validate ownership:

```python
ticket = get_object_or_404(
    Ticket,
    slug=slug,
    student_id=request.user.profile.student_id,
    org=request.user.profile.org
)
```

### 4. Log Access
Use `UserActivity` to log important actions for audit trails.

### 5. CSRF Protection
All POST requests must include CSRF tokens.

---

## Common Patterns

### Pattern 1: Role-Based Redirects

```python
def get_dashboard_url(user):
    if user.profile.is_central_admin:
        return reverse('central_admin:dashboard')
    elif user.profile.is_institution_admin:
        return reverse('institution_admin:dashboard')
    elif user.profile.is_driver:
        return reverse('drivers:dashboard')
    else:
        return reverse('students:dashboard')
```

### Pattern 2: Conditional Forms

```python
class TicketForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user and user.profile.is_central_admin:
            # Admin can edit more fields
            pass
        else:
            # Students have limited fields
            del self.fields['status']
```

### Pattern 3: Scoped Querysets

```python
def get_queryset(self):
    qs = super().get_queryset()
    user = self.request.user
    
    # Always filter by org
    qs = qs.filter(org=user.profile.org)
    
    # Additional role-based filtering
    if user.profile.is_institution_admin:
        qs = qs.filter(institution=user.profile.institution)
    elif user.profile.is_student:
        qs = qs.filter(student_id=user.profile.student_id)
    
    return qs
```

---

## Testing Roles

```python
# In tests
from django.test import TestCase
from core.models import User, UserProfile

class RoleTestCase(TestCase):
    def test_central_admin_access(self):
        user = User.objects.create_user(email='admin@test.com')
        profile = UserProfile.objects.create(
            user=user,
            org=self.org,
            role=UserProfile.CENTRAL_ADMIN
        )
        
        self.assertTrue(profile.is_central_admin)
        
        self.client.force_login(user)
        response = self.client.get(reverse('central_admin:dashboard'))
        self.assertEqual(response.status_code, 200)
```

---

## Next Steps

- **Backend Development**: Read [Backend Development](./06-backend-development.md)
- **Frontend Development**: See [Frontend Development](./07-frontend-development.md)
- **Testing**: Review [Testing Guide](./09-testing.md)
