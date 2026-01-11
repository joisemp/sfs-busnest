# Data Models

This document provides comprehensive documentation of all database models in the SFS BusNest system.

## Model Organization

Models are organized across 10 files in `src/services/models/`:

1. **core.py** - Organisation, Institution
2. **routes.py** - Route, Stop, RouteFile
3. **registrations.py** - Registration, Schedule, ScheduleGroup
4. **buses.py** - Bus, RefuelingRecord, BusFile
5. **bus_operations.py** - BusRecord, Trip
6. **tickets.py** - Ticket, InstallmentDate, Payment, StudentGroup, Receipt, ReceiptFile
7. **requests.py** - FAQ, BusRequest, BusRequestComment
8. **reservations.py** - BusReservationRequest, BusReservationAssignment, TripExpense
9. **system.py** - ExportedFile, UserActivity, Notification, StudentPassFile
10. **utils.py** - Utility functions

All models are re-exported in `__init__.py` for convenient importing.

## Entity Relationship Diagram

```
Organisation
  │
  ├─── Institution
  │      └─── StudentGroup
  │
  ├─── Registration
  │      ├─── Route
  │      │      ├─── Stop
  │      │      └─── RouteFile
  │      ├─── Schedule
  │      ├─── ScheduleGroup
  │      ├─── BusRecord
  │      │      └─── Trip
  │      ├─── Receipt
  │      │      └─── ReceiptFile
  │      └─── Ticket
  │             └─── Payment
  │
  ├─── Bus
  │      ├─── RefuelingRecord
  │      └─── BusFile
  │
  ├─── BusRequest
  │      └─── BusRequestComment
  │
  ├─── BusReservationRequest
  │      ├─── BusReservationAssignment
  │      └─── TripExpense
  │
  └─── System Models
         ├─── Notification
         ├─── UserActivity
         ├─── ExportedFile
         └─── StudentPassFile
```

## Core Models

### Organisation

**File**: `services/models/core.py`

Represents an organization (top-level entity in multi-tenancy).

```python
class Organisation(models.Model):
    name = CharField(max_length=255, unique=True)
    slug = SlugField(unique=True, db_index=True)
    address = TextField(blank=True, null=True)
    phone = CharField(max_length=20, blank=True, null=True)
    email = EmailField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Root entity for multi-tenancy
- All other models reference this via `org` field
- Unique slug auto-generated on save

**Relationships**:
- Has many: Institutions, Registrations, Buses, BusRequests

---

### Institution

**File**: `services/models/core.py`

Represents an educational institution within an organization.

```python
class Institution(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    name = CharField(max_length=255)
    slug = SlugField(unique=True, db_index=True)
    address = TextField(blank=True, null=True)
    phone = CharField(max_length=20, blank=True, null=True)
    email = EmailField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Belongs to one organization
- Has many student groups
- Institution admins manage their institution

**Relationships**:
- Belongs to: Organisation
- Has many: StudentGroups, UserProfiles

---

## Route Models

### Route

**File**: `services/models/routes.py`

Represents a bus route with multiple stops.

```python
class Route(models.Model):
    registration = ForeignKey(Registration, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    name = CharField(max_length=255)
    slug = SlugField(unique=True, db_index=True)
    description = TextField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Belongs to a registration
- Contains multiple stops
- Routes are registration-specific

**Relationships**:
- Belongs to: Registration, Organisation
- Has many: Stops, RouteFiles, Trips

---

### Stop

**File**: `services/models/routes.py`

Represents a stop along a route.

```python
class Stop(models.Model):
    route = ForeignKey(Route, on_delete=CASCADE, related_name='stops')
    org = ForeignKey(Organisation, on_delete=CASCADE)
    name = CharField(max_length=255)
    slug = SlugField(unique=True, db_index=True)
    order = PositiveIntegerField(default=0)
    latitude = DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Belongs to one route
- Can be transferred to another route
- Order determines sequence along route
- Transferring updates all associated tickets

**Relationships**:
- Belongs to: Route, Organisation
- Referenced by: Tickets (pickup_stop, drop_stop)

---

### RouteFile

**File**: `services/models/routes.py`

Stores Excel files uploaded for route creation.

```python
class RouteFile(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    registration = ForeignKey(Registration, on_delete=CASCADE)
    file = FileField(upload_to=rename_uploaded_file, validators=[validate_excel_file])
    uploaded_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Processed asynchronously by Celery
- Creates routes and stops from Excel data
- One-time upload per file

---

## Registration Models

### Registration

**File**: `services/models/registrations.py`

Represents a booking period/event.

```python
class Registration(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    name = CharField(max_length=255)
    slug = SlugField(unique=True, db_index=True)
    code = CharField(max_length=20, unique=True)  # For student access
    description = TextField(blank=True, null=True)
    start_date = DateField()
    end_date = DateField()
    is_active = BooleanField(default=False)  # Only one active at a time
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Only one active registration per organization
- Unique code for student access
- Time-bound (start and end dates)
- Code generated via `generate_unique_code()`

**Relationships**:
- Belongs to: Organisation
- Has many: Routes, Schedules, ScheduleGroups, BusRecords, Tickets, Receipts

---

### Schedule

**File**: `services/models/registrations.py`

Represents a time-based schedule (morning, evening, etc.).

```python
class Schedule(models.Model):
    registration = ForeignKey(Registration, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    name = CharField(max_length=100)
    slug = SlugField(unique=True, db_index=True)
    schedule_type = CharField(max_length=20, choices=[('pickup', 'Pickup'), ('drop', 'Drop')])
    start_time = TimeField()
    end_time = TimeField()
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Either pickup or drop schedule
- Time range for the schedule
- Combined with routes to create trips

**Relationships**:
- Belongs to: Registration, Organisation
- Referenced by: Trips, ScheduleGroups

---

### ScheduleGroup

**File**: `services/models/registrations.py`

Groups pickup and drop schedules together.

```python
class ScheduleGroup(models.Model):
    registration = ForeignKey(Registration, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    name = CharField(max_length=100)
    slug = SlugField(unique=True, db_index=True)
    pickup_schedule = ForeignKey(Schedule, on_delete=CASCADE, related_name='pickup_groups')
    drop_schedule = ForeignKey(Schedule, on_delete=CASCADE, related_name='drop_groups')
    allow_one_way = BooleanField(default=False)  # Allow pickup only or drop only
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Pairs pickup and drop schedules
- `allow_one_way` enables booking just pickup or drop
- Students select schedule groups during booking

**Relationships**:
- Belongs to: Registration, Organisation
- References: Schedules (pickup and drop)

---

## Bus Models

### Bus

**File**: `services/models/buses.py`

Represents a bus in the organization's fleet.

```python
class Bus(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    bus_number = CharField(max_length=50, unique=True)
    slug = SlugField(unique=True, db_index=True)
    capacity = PositiveIntegerField()
    model = CharField(max_length=100, blank=True, null=True)
    registration_number = CharField(max_length=50, blank=True, null=True)
    is_available = BooleanField(default=True)  # Soft delete
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Organization-level resource
- Can be assigned to multiple registrations
- `is_available` used for soft deletes
- `capacity` defines maximum seats

**Relationships**:
- Belongs to: Organisation
- Has many: BusRecords, RefuelingRecords

---

### RefuelingRecord

**File**: `services/models/buses.py`

Tracks refueling activities for buses (driver-managed).

```python
class RefuelingRecord(models.Model):
    bus = ForeignKey(Bus, on_delete=CASCADE, related_name='refueling_records')
    org = ForeignKey(Organisation, on_delete=CASCADE)
    driver = ForeignKey(User, on_delete=SET_NULL, null=True)
    slug = SlugField(unique=True, db_index=True)
    date = DateField()
    odometer_reading = PositiveIntegerField()
    fuel_quantity = DecimalField(max_digits=10, decimal_places=2)
    fuel_cost = DecimalField(max_digits=10, decimal_places=2)
    notes = TextField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Drivers log refueling for their assigned bus
- Tracks fuel consumption and costs
- Helps with maintenance and budgeting

**Relationships**:
- Belongs to: Bus, Organisation
- Created by: Driver (User)

---

### BusFile

**File**: `services/models/buses.py`

Stores Excel files for bulk bus uploads.

```python
class BusFile(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    file = FileField(upload_to=rename_bus_uploaded_file, validators=[validate_excel_file])
    uploaded_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Processed asynchronously by Celery
- Creates multiple buses from Excel data

---

## Bus Operations Models

### BusRecord

**File**: `services/models/bus_operations.py`

Links a bus to a specific registration.

```python
class BusRecord(models.Model):
    bus = ForeignKey(Bus, on_delete=CASCADE)
    registration = ForeignKey(Registration, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    slug = SlugField(unique=True, db_index=True)
    driver = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True)
    min_required_capacity = PositiveIntegerField(default=0)  # Auto-calculated
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('bus', 'registration')
```

**Key Points**:
- One bus can be in multiple registrations
- `min_required_capacity` auto-calculated from trip bookings
- Driver assigned to bus record
- Creates trips when combined with routes and schedules

**Relationships**:
- Belongs to: Bus, Registration, Organisation
- Has many: Trips
- Assigned to: Driver (User)

---

### Trip

**File**: `services/models/bus_operations.py`

Represents a specific trip (route + schedule + bus).

```python
class Trip(models.Model):
    registration = ForeignKey(Registration, on_delete=CASCADE)
    bus_record = ForeignKey(BusRecord, on_delete=CASCADE)
    route = ForeignKey(Route, on_delete=CASCADE)
    schedule = ForeignKey(Schedule, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    slug = SlugField(unique=True, db_index=True)
    booking_count = PositiveIntegerField(default=0)  # Current bookings
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('registration', 'bus_record', 'route', 'schedule')
```

**Key Points**:
- Unique combination of registration, bus_record, route, schedule
- `booking_count` tracks current seat allocation
- Capacity checked against `bus_record.bus.capacity`
- Updated when tickets are created/deleted

**Relationships**:
- Belongs to: Registration, BusRecord, Route, Schedule, Organisation
- Referenced by: Tickets

---

## Ticket & Payment Models

### Ticket

**File**: `services/models/tickets.py`

Represents a student's bus booking.

```python
class Ticket(models.Model):
    registration = ForeignKey(Registration, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    student_id = CharField(max_length=50)
    student_name = CharField(max_length=255)
    student_email = EmailField(blank=True, null=True)
    student_phone = CharField(max_length=20, blank=True, null=True)
    student_group = ForeignKey(StudentGroup, on_delete=SET_NULL, null=True)
    institution = ForeignKey(Institution, on_delete=SET_NULL, null=True)
    
    pickup_route = ForeignKey(Route, on_delete=SET_NULL, null=True, related_name='pickup_tickets')
    pickup_stop = ForeignKey(Stop, on_delete=SET_NULL, null=True, related_name='pickup_tickets')
    pickup_schedule = ForeignKey(Schedule, on_delete=SET_NULL, null=True, related_name='pickup_tickets')
    pickup_bus_record = ForeignKey(BusRecord, on_delete=SET_NULL, null=True, related_name='pickup_tickets')
    
    drop_route = ForeignKey(Route, on_delete=SET_NULL, null=True, related_name='drop_tickets')
    drop_stop = ForeignKey(Stop, on_delete=SET_NULL, null=True, related_name='drop_tickets')
    drop_schedule = ForeignKey(Schedule, on_delete=SET_NULL, null=True, related_name='drop_tickets')
    drop_bus_record = ForeignKey(BusRecord, on_delete=SET_NULL, null=True, related_name='drop_tickets')
    
    slug = SlugField(unique=True, db_index=True)
    status = CharField(max_length=20, choices=[...], default='confirmed')
    total_amount = DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Contains all student and booking information
- Separate pickup and drop details (can be same or different)
- Status: confirmed, cancelled, completed
- Connected to payment installments
- Deleting triggers signal to update trip counts

**Relationships**:
- Belongs to: Registration, Organisation
- References: Routes, Stops, Schedules, BusRecords (pickup and drop)
- Has many: Payments

---

### Payment

**File**: `services/models/tickets.py`

Tracks payment installments for a ticket.

```python
class Payment(models.Model):
    ticket = ForeignKey(Ticket, on_delete=CASCADE, related_name='payments')
    org = ForeignKey(Organisation, on_delete=CASCADE)
    installment_date = ForeignKey(InstallmentDate, on_delete=CASCADE)
    amount = DecimalField(max_digits=10, decimal_places=2)
    payment_date = DateField()
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Multiple payments per ticket (installments)
- Linked to installment dates
- Tracks actual payment amounts

**Relationships**:
- Belongs to: Ticket, Organisation
- References: InstallmentDate

---

### StudentGroup

**File**: `services/models/tickets.py`

Represents class-section combinations.

```python
class StudentGroup(models.Model):
    institution = ForeignKey(Institution, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    name = CharField(max_length=100)  # Format: "5 - A"
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Format: "{CLASS} - {SECTION}" (e.g., "5 - A")
- Case-insensitive during Excel processing
- Belongs to one institution

**Relationships**:
- Belongs to: Institution, Organisation
- Referenced by: Tickets

---

### Receipt

**File**: `services/models/tickets.py`

Validates student eligibility for booking.

```python
class Receipt(models.Model):
    registration = ForeignKey(Registration, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    student_id = CharField(max_length=50)
    student_group = ForeignKey(StudentGroup, on_delete=CASCADE)
    amount_paid = DecimalField(max_digits=10, decimal_places=2)
    issue_date = DateField()
    expiry_date = DateField()
    is_expired = BooleanField(default=False)
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Students need valid receipt to book
- Receipt `student_id` must match booking `student_id`
- Automatically marked expired via Celery Beat task
- Uploaded via Excel files

**Relationships**:
- Belongs to: Registration, Organisation
- References: StudentGroup

---

### ReceiptFile

**File**: `services/models/tickets.py`

Stores Excel files for receipt uploads.

```python
class ReceiptFile(models.Model):
    registration = ForeignKey(Registration, on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE)
    file = FileField(upload_to=rename_uploaded_file_receipt, validators=[validate_excel_file])
    uploaded_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Processed asynchronously by Celery
- Creates receipts and student groups from Excel

---

## Request Models

### BusRequest

**File**: `services/models/requests.py`

Support tickets/FAQs from users.

```python
class BusRequest(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    user = ForeignKey(User, on_delete=CASCADE)
    subject = CharField(max_length=255)
    description = TextField()
    status = CharField(max_length=20, choices=[...], default='open')
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Status: open, in_progress, resolved, closed
- Users can ask questions or report issues
- Admins respond via comments

**Relationships**:
- Belongs to: Organisation, User
- Has many: BusRequestComments

---

### BusRequestComment

**File**: `services/models/requests.py`

Comments/responses on bus requests.

```python
class BusRequestComment(models.Model):
    request = ForeignKey(BusRequest, on_delete=CASCADE, related_name='comments')
    org = ForeignKey(Organisation, on_delete=CASCADE)
    user = ForeignKey(User, on_delete=CASCADE)
    comment = TextField()
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Multiple comments per request
- Both users and admins can comment

**Relationships**:
- Belongs to: BusRequest, Organisation, User

---

## Reservation Models

### BusReservationRequest

**File**: `services/models/reservations.py`

Requests for bus reservations (special events).

```python
class BusReservationRequest(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    institution = ForeignKey(Institution, on_delete=CASCADE)
    requested_by = ForeignKey(User, on_delete=CASCADE)
    reservation_no = CharField(max_length=20, unique=True)  # Auto-generated
    slug = SlugField(unique=True, db_index=True)
    purpose = CharField(max_length=255)
    description = TextField()
    from_date = DateField()
    to_date = DateField()
    from_location = CharField(max_length=255)
    to_location = CharField(max_length=255)
    estimated_distance = PositiveIntegerField()
    number_of_buses = PositiveIntegerField()
    status = CharField(max_length=20, choices=[...], default='pending')
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Points**:
- Institution admins create requests
- Central admin assigns buses
- Status: pending, approved, rejected, completed
- `reservation_no` auto-generated on save

**Relationships**:
- Belongs to: Organisation, Institution
- Created by: User
- Has many: BusReservationAssignments, TripExpenses

---

### BusReservationAssignment

**File**: `services/models/reservations.py`

Assigns buses to reservation requests.

```python
class BusReservationAssignment(models.Model):
    reservation_request = ForeignKey(BusReservationRequest, on_delete=CASCADE, related_name='bus_assignments')
    org = ForeignKey(Organisation, on_delete=CASCADE)
    bus = ForeignKey(Bus, on_delete=CASCADE)
    assigned_by = ForeignKey(User, on_delete=CASCADE)
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Links buses to reservation requests
- Central admin creates assignments

**Relationships**:
- Belongs to: BusReservationRequest, Organisation, Bus
- Created by: User

---

### TripExpense

**File**: `services/models/reservations.py`

Tracks expenses for reservation trips.

```python
class TripExpense(models.Model):
    reservation_request = ForeignKey(BusReservationRequest, on_delete=CASCADE, related_name='trip_expenses')
    org = ForeignKey(Organisation, on_delete=CASCADE)
    bus_assignment = ForeignKey(BusReservationAssignment, on_delete=CASCADE)
    expense_type = CharField(max_length=50)  # fuel, toll, maintenance, etc.
    amount = DecimalField(max_digits=10, decimal_places=2)
    description = TextField(blank=True, null=True)
    date = DateField()
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Tracks various expense types
- Linked to specific bus assignments

**Relationships**:
- Belongs to: BusReservationRequest, Organisation, BusReservationAssignment

---

## System Models

### Notification

**File**: `services/models/system.py`

In-app notifications for users.

```python
class Notification(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    user = ForeignKey(User, on_delete=CASCADE)
    title = CharField(max_length=255)
    message = TextField()
    notification_type = CharField(max_length=20, choices=[...])
    is_read = BooleanField(default=False)
    priority = CharField(max_length=20, choices=[...], default='normal')
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Types: info, success, warning, error
- Priority: low, normal, high
- HTMX loads priority notifications on page load

**Relationships**:
- Belongs to: Organisation, User

---

### UserActivity

**File**: `services/models/system.py`

Audit log of all user actions.

```python
class UserActivity(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    user = ForeignKey(User, on_delete=SET_NULL, null=True)
    action = CharField(max_length=255)
    description = TextField()
    ip_address = GenericIPAddressField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Logs all important actions
- Tracks IP addresses
- Used for compliance and debugging

**Relationships**:
- Belongs to: Organisation
- Related to: User (nullable)

---

### ExportedFile

**File**: `services/models/system.py`

Stores generated reports and exports.

```python
class ExportedFile(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    file = FileField(upload_to=rename_exported_file)
    file_type = CharField(max_length=50)  # excel, pdf, csv
    description = CharField(max_length=255)
    generated_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- Generated by Celery tasks
- Downloadable by users
- Automatic cleanup (future)

**Relationships**:
- Belongs to: Organisation
- Generated by: User

---

### StudentPassFile

**File**: `services/models/system.py`

Stores generated student bus passes.

```python
class StudentPassFile(models.Model):
    org = ForeignKey(Organisation, on_delete=CASCADE)
    ticket = ForeignKey(Ticket, on_delete=CASCADE)
    file = FileField(upload_to=rename_student_pass_file)
    generated_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    slug = SlugField(unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Points**:
- One pass per ticket
- PDF format
- Generated on demand

**Relationships**:
- Belongs to: Organisation, Ticket
- Generated by: User

---

## Common Model Fields

All models include:

- **org**: ForeignKey to Organisation (multi-tenancy)
- **slug**: Unique slug for URLs (auto-generated)
- **created_at**: Timestamp of creation
- **updated_at**: Timestamp of last update (where applicable)

## Model Conventions

### Slug Generation
```python
from config.utils import generate_unique_slug

def save(self, *args, **kwargs):
    if not self.slug:
        self.slug = generate_unique_slug(self.__class__, self.name)
    super().save(*args, **kwargs)
```

### Organisation Filter
```python
# Always filter by organisation
queryset = Model.objects.filter(org=request.user.profile.org)
```

### Soft Deletes
```python
# Use status or boolean flags instead of deletion
model.is_available = False
model.save()
```

### Signal Handlers
```python
@receiver(post_delete, sender=Ticket)
def update_trip_booking_count(sender, instance, **kwargs):
    # Auto-update trip counts
```

## Database Indexes

Key indexes for performance:

- All `slug` fields: `db_index=True`
- Foreign keys: Automatic indexes
- `unique_together` on BusRecord, Trip

## Migrations

```bash
# Create migrations
docker exec -it sfs-busnest-container python manage.py makemigrations

# Apply migrations
docker exec -it sfs-busnest-container python manage.py migrate

# View migration status
docker exec -it sfs-busnest-container python manage.py showmigrations
```

## Next Steps

- **Permissions**: See [User Roles & Permissions](./05-roles-permissions.md)
- **Backend**: Read [Backend Development](./06-backend-development.md)
- **Testing**: Review [Testing Guide](./09-testing.md)
