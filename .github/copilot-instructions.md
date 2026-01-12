# SFS BusNest - AI Coding Agent Instructions

## Project Overview
SFS BusNest is a Django-based centralized bus management system for multiple educational institutions. It manages student registration, bus seat allocation, route planning, and automated booking across shared bus services.

**Key Design Principle**: Multi-tenancy at the organization level with role-based access (Central Admin, Institution Admin, Students).

## Architecture

### Project Structure
```
src/
  ├─ config/          # Django settings, Celery config, utilities
  │   ├─ middleware/  # Custom middleware (maintenance mode)
  │   └─ mixins/      # Access control mixins, form mixins
  ├─ core/            # Custom user authentication
  ├─ services/        # Main business logic (30+ models)
  │   ├─ models/      # 10 modular files (core, routes, registrations, etc.)
  │   ├─ views/       # Role-specific views (central_admin, institution_admin, drivers, students)
  │   ├─ forms/       # Role-specific forms matching view structure
  │   ├─ urls/        # Role-specific URL configs
  │   ├─ utils/       # Utility functions (transfer_stop.py, etc.)
  │   └─ tasks.py     # Celery background tasks
  ├─ templates/       # Role-based template directories
  └─ static/          # SCSS, JS, images, vendor libs
```

### Core Components
- **`core/`**: Custom user authentication (`User` with email as USERNAME_FIELD, `UserProfile` with single role field)
- **`services/`**: Main business logic - 30+ models organized across 10 modules (core, routes, registrations, buses, bus_operations, tickets, requests, reservations, system, utils)
- **`config/`**: Settings, Celery config, middleware (maintenance mode), validators, utils, mixins (access control)

### User Roles & Access Pattern
```python
# Four distinct user types with separate URL namespaces
UserProfile.is_central_admin    # Full system access - manages all institutions
UserProfile.is_institution_admin # Institution-scoped - manages their institution only
UserProfile.is_driver           # Driver dashboard - manages refueling records, views assigned trips
UserProfile.is_student          # Read-only access - views their tickets/schedules
```

**URL Structure**: `/central_admin/`, `/institution_admin/`, `/drivers/`, `/students/` - each with separate views/forms/urls modules in `services/`

### Data Hierarchy
```
Organisation (org)
  ├─ Institution(s)
  │   ├─ StudentGroup(s) (class-section combinations)
  │   └─ UserProfile(s) (institution admins, drivers, students)
  ├─ Registration (booking period/event)
  │   ├─ Route(s) → Stop(s)
  │   │   └─ RouteFile(s) (Excel uploads for route data)
  │   ├─ Schedule(s) (morning/evening timings)
  │   ├─ ScheduleGroup(s) (pickup+drop pairs)
  │   ├─ BusRecord(s) (bus assigned to registration)
  │   │   └─ Trip(s) (route+schedule+bus combination)
  │   ├─ Receipt(s) (payment validation)
  │   │   └─ ReceiptFile(s) (Excel uploads for receipt data)
  │   ├─ Ticket(s) (student bookings)
  │   │   └─ Payment(s) (installment payments)
  │   └─ BusReservationRequest(s) (institution bus requests)
  │       ├─ BusReservationAssignment(s) (bus allocations)
  │       └─ TripExpense(s) (trip cost tracking)
  ├─ Bus(es) (organization fleet)
  │   ├─ RefuelingRecord(s) (fuel tracking by drivers)
  │   └─ BusFile(s) (Excel uploads for bus data)
  ├─ BusRequest(s) (FAQ/support tickets)
  │   └─ BusRequestComment(s) (ticket responses)
  └─ System Models
      ├─ Notification(s) (in-app notifications)
      ├─ UserActivity(s) (audit log)
      ├─ ExportedFile(s) (generated reports)
      └─ StudentPassFile(s) (generated passes)
```

**Critical**: All models have `org` ForeignKey - filter by `user.profile.org` for multi-tenancy. Use `slug` for URLs (all models auto-generate unique slugs on save).

## Development Workflows

### Local Development Setup
```bash
# Prerequisites: Docker & Docker Compose installed
docker compose build
docker compose up

# Access:
# - App: http://localhost:7000
# - Flower (Celery monitoring): http://localhost:5555 (admin:password123)
# - Postgres: localhost:5432 (postgres:postgres)
# - Redis: localhost:6379
```

**Environment Variables**: Create `src/config/.env` with:
```env
ENVIRONMENT=development
SECRET_KEY=your_secret_key
```

### Testing
```bash
# Windows (PowerShell)
cd src; $env:DJANGO_SETTINGS_MODULE="config.test_settings"; python manage.py test; $env:DJANGO_SETTINGS_MODULE="config.settings"

# Uses separate test_settings.py - always run before committing
```

### Migrations
```python
# Auto-run on container start via docker-compose command
# Manual: docker exec sfs-busnest-container python manage.py makemigrations
```

## Key Patterns & Conventions

### Model Conventions
1. **Modular Organization**: Models split across 10 files in `services/models/` (core.py, routes.py, registrations.py, buses.py, bus_operations.py, tickets.py, requests.py, reservations.py, system.py, utils.py)
2. **Unique Slugs**: All models use `slug = SlugField(unique=True, db_index=True)` with auto-generation in `save()` via `config.utils.generate_unique_slug()`
3. **Unique Codes**: Registration uses `generate_unique_code()` for shareable booking codes; BusReservationRequest auto-generates `reservation_no`
4. **Organisation Scoping**: Always filter by `org=request.user.profile.org` in views (multi-tenancy enforcement)
5. **Soft Deletes**: Use `is_available` (Bus), `is_expired` (Receipt), `status` (Ticket) instead of hard deletes
6. **Signals**: `Ticket` deletion auto-decrements `Trip.booking_count` via `update_trip_booking_count_on_ticket_delete` signal
7. **Role-Based Model**: UserProfile uses single `role` field (CharField with choices) instead of multiple boolean flags

### File Upload Processing
**Pattern**: Upload → Celery task → Notification

```python
# All file uploads validated with config.validators.validate_excel_file
# Processed asynchronously via Celery tasks in services/tasks.py:
# - process_uploaded_route_excel (creates Route/Stop from Excel)
# - process_uploaded_receipt_data_excel (creates Receipt/StudentGroup)
# - process_uploaded_bus_excel (bulk bus creation)

# File naming: Use custom upload_to functions (rename_uploaded_file, etc.)
# Notification pattern: Create notification → process → update notification with results
```

### Celery Background Tasks
```python
# Defined in services/tasks.py, registered in config/celery.py
# Key tasks:
# - File processing (Excel imports)
# - Email sending (send_email_task)
# - Scheduled jobs (mark_expired_receipts via django-celery-beat)
# - Exports (export_tickets_to_excel, generate_student_pass)

# Always log progress and create Notification for user feedback
```

### Utility Functions
**Transfer Stop Utility** (`services/utils/transfer_stop.py`):
```python
def move_stop_and_update_tickets(stop, new_route, user):
    """
    Transfer stop to new route and update all associated tickets.
    
    Key Logic:
    - Wraps everything in @transaction.atomic()
    - Determines transfer type (pickup/drop/both) by comparing old vs new routes
    - Only updates relevant bus records (selective updates)
    - Validates route-specific trips exist before assignment
    - Updates Trip.booking_count on source and target routes
    - Logs activity for audit trail
    
    Returns: (success: bool, message: str, updated_count: int)
    """
```

**Route Sorting** (`services/views/central_admin.py`):
```python
def _natural_sort_key(text):
    """Natural/alphanumeric sorting for routes."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
    
# Usage:
routes = routes.order_by('name')
routes = sorted(routes, key=lambda r: _natural_sort_key(r.name))
```

### Form Handling
Forms split by role: `services/forms/{central_admin,institution_admin,drivers,students}.py`

**HTMX Integration**: Many forms use HTMX for dynamic updates (check templates for `hx-` attributes)

### Access Control Mixins
**Location**: `config/mixins/access_mixin.py`

Provides role-based view access control:
- `CentralAdminOnlyAccessMixin`: Restricts access to central admins
- `InsitutionAdminOnlyAccessMixin`: Restricts access to institution admins (note the typo - missing 't')
- `DriverOnlyAccessMixin`: Restricts access to drivers
- `RegistrationOpenCheckMixin`: Used for student-facing views - validates active registration exists
- `RegistrationClosedOnlyAccessMixin`: Restricts access when registration is closed
- `RedirectLoggedInUsersMixin`: Redirects authenticated users to role-specific dashboards

**Note**: Student views use `RegistrationOpenCheckMixin` instead of a dedicated student mixin. They don't require authentication - access is based on active registration status.

All admin/driver views should inherit from appropriate mixin + `LoginRequiredMixin`

### Static Files
- **Development**: WhiteNoise serves from `src/static/` and `src/staticfiles/`
- **Production**: DigitalOcean Spaces (S3-compatible) via `django-storages`
- **Technologies**: Bootstrap 5, SCSS, vanilla JS, HTMX (no React/Vue)

## Key Features

### Driver Dashboard & Refueling Management
**Location**: `templates/drivers/` + `services/views/drivers.py`

Driver-specific functionality for managing assigned buses and refueling records:

**Features**:
1. **Driver Dashboard**: Shows driver profile, assigned bus record from active registration, quick access to tasks
2. **Refueling Records**: Drivers can add/update refueling records for their assigned bus
   - Fields: date, odometer_reading, fuel_quantity, fuel_cost, notes
   - Auto-generates unique slug on save
   - Scoped to driver's assigned bus in active registration
3. **Access Pattern**: Only one registration is active at a time (`Registration.is_active=True`)
   - Each driver assigned to one bus record in active registration
   - All operations scoped to assigned bus

**Views** (`services/views/drivers.py`):
- `DriverDashboardView`: Main dashboard for drivers
- `DriverRefuelingListView`: List all refueling records for driver's bus
- `DriverRefuelingCreateView`: Add new refueling record
- `DriverRefuelingUpdateView`: Edit existing refueling record

**URL Namespace**: `/drivers/` (dashboard, refueling list, refueling create/update)

**Models**:
- `RefuelingRecord` in `services/models/buses.py`: Tracks fuel consumption, costs, odometer readings
- `UserProfile.years_of_experience`: Optional field for driver experience tracking

### Stop Transfer Management System
**Location**: `templates/central_admin/stop_transfer_management.html` + `static/js/stop_transfer.js`

Complete drag-and-drop interface for managing stops across routes with real-time updates:

**Features**:
1. **Drag & Drop Transfer**: HTML5 drag-and-drop to move stops between routes
   - Visual feedback during drag (opacity, cursor changes)
   - Drop zones highlight on hover
   - Bootstrap modal confirmation before transfer
   
2. **Inline Stop Editing**: Double-click stop name to edit in-place
   - Enter to save, Escape to cancel
   - Real-time API update with optimistic UI
   
3. **Add Stops**: Add new stops to any route via modal form
   - Validation for duplicate names within route
   - Dynamic UI update without page refresh
   
4. **Delete Stops**: Remove stops with zero ticket associations
   - Button only shows for stops with 0 pickups and 0 drops
   - Confirmation modal with danger styling
   - Backend validation before deletion
   
5. **Natural Route Sorting**: Routes display in natural order (1, 2, 3... 10, 11, not 1, 10, 11, 2)
   - Uses regex-based alphanumeric sorting: `re.split(r'(\d+)', text)`

**Backend Logic** (`services/utils/transfer_stop.py`):
- `move_stop_and_update_tickets()`: Atomic transaction handling stop transfer with selective bus record updates
- **Selective Updates**: Only updates relevant bus records based on transfer type:
  - Pickup stop transferred → updates only `pickup_bus_record`
  - Drop stop transferred → updates only `drop_bus_record`  
  - Both pickup & drop same → updates both records
- **Route-Specific Validation**: Ensures tickets only assigned to bus records with trips on the target route
- **Trip Count Management**: Auto-updates `Trip.booking_count` on source and target routes

**API Endpoints** (all in `services/views/central_admin.py`):
- `TransferStopAPIView`: POST - Transfer stop between routes
- `UpdateStopNameAPIView`: POST - Update stop name
- `AddStopAPIView`: POST - Create new stop in route
- `DeleteStopAPIView`: POST - Delete stop (validates no tickets)
- `StopTransferManagementView`: GET - Main interface

**JavaScript Architecture** (`static/js/stop_transfer.js`):
- **State Management**: `draggedStopData`, `pendingTransfer`, `pendingAddStop`, `pendingDeleteStop`
- **Event Handlers**: Drag events, inline editing, modal confirmations
- **Drag Prevention**: Buttons have `draggable="false"` and drag events are cancelled when clicking buttons
- **Bootstrap Modals**: Professional confirmation dialogs for all destructive actions
- **Error Handling**: Comprehensive try-catch with fallbacks for modal display

**SCSS Styling** (`static/styles/central_admin/stop_transfer/style.scss`):
- **SASS 2.0 Compatible**: Uses `color.scale()` instead of deprecated `lighten()`/`darken()`
- **Vertical Layout**: `.stop-info` uses flex-column to stack name above buttons/indicators
- **Drag States**: `.dragging`, `.drag-active`, `.drag-over` classes for visual feedback
- **Responsive Grid**: Auto-fit grid for route cards (min 350px columns)
- **Animations**: Smooth transitions, scale effects on buttons

**Critical Implementation Notes**:
- Always wrap transfers in `@transaction.atomic()` for data integrity
- Log all operations with `log_user_activity()` for audit trail
- Use `word-break: break-word` on stop names to prevent overflow with long names
- Modal initialization requires checking for existing instance: `bootstrap.Modal.getInstance()` before creating new
- Event delegation doesn't work well with dynamically added buttons - attach listeners directly after DOM insertion

## Common Gotchas

1. **Trip Booking Count**: Must manually increment/decrement `Trip.booking_count` when creating/deleting tickets
2. **BusRecord.min_required_capacity**: Auto-calculated on save based on max `Trip.booking_count` - don't set manually
3. **Receipt Validation**: Students need valid non-expired `Receipt` matching their `student_id` before booking
4. **Schedule Groups**: `allow_one_way` flag determines if students can book only pickup or drop
5. **Student Group Format**: Always `"{CLASS} - {SECTION}"` (e.g., "5 - A"), case-insensitive in Excel processing
6. **File Storage**: Use `default_storage.open()` for cloud compatibility in Celery tasks
7. **Stop Transfers**: When transferring stops, only update relevant bus records (pickup vs drop) to avoid unnecessary ticket modifications
8. **Drag & Drop**: Always prevent drag events on interactive elements (buttons, inputs) using `e.target.closest('button')` check
9. **Bootstrap Modals**: Check for existing modal instances before creating new ones to prevent memory leaks
10. **Role System**: Use `profile.role` (single CharField) not boolean flags - use properties `is_central_admin`, `is_driver`, etc. for backward compatibility
11. **Driver Access**: Drivers can only access their assigned bus in the active registration - always check `Registration.is_active=True`
12. **Model Imports**: Import from `services.models` (uses `__init__.py` re-exports), not from individual model files
13. **Access Mixin Typo**: The institution admin mixin class name has a typo: `InsitutionAdminOnlyAccessMixin` (missing 't' in "Institution")
14. **Student Views**: Student-facing views use `RegistrationOpenCheckMixin` and don't require authentication - they're public during active registration periods

## Database

**PostgreSQL** (required - not SQLite compatible due to specific features used)

**Key Indexes**: `db_index=True` on all slugs, `unique_together` constraints on (bus, registration), (registration, record, schedule)

## Deployment

**Production Stack**: Django + Gunicorn + PostgreSQL + Redis + Celery + Flower
**Hosting**: Digital Ocean / Railway
**Email**: Mailjet SMTP (console backend in dev)

**Settings Split**: 
- `ENVIRONMENT=development` → local DB/Redis, console email
- `ENVIRONMENT=production` → DATABASE_URL, REDIS_URL, SMTP email, S3 storage

## Frontend Architecture & Templates

### Template Structure
**Four-layer base template inheritance**:
```
base.html (global layout)
  ├─ central_admin/ (extends base.html)
  ├─ institution_admin/ (extends base.html)
  ├─ drivers/ (extends base.html)
  └─ students/ (extends base.html)
```

**Base Template Pattern** (`templates/base.html`):
- Fixed header (60px height) with logo, notifications dropdown, profile menu
- Role-specific sidebar (220px width, collapses on mobile)
- Main content area with HTMX priority notifications loader
- Django messages framework integration (alert-{danger|success|warning|info})

**Responsive Breakpoints**:
- Desktop: Sidebar 220px wide
- Tablet (431px-1024px): Sidebar 90px wide (icons only)
- Mobile (<430px): Bottom navigation bar (76px height)

### HTMX Usage Patterns
```html
<!-- Dynamic dropdown loading (student group filter) -->
<select hx-get="{% url 'central_admin:student_group_filter' %}" 
        hx-target="#student-group-container" 
        hx-trigger="change">

<!-- Auto-load priority notifications on page load -->
<div hx-get="{% url 'core:priority_notifications' %}" 
     hx-trigger="load" 
     hx-target="#priority-notifications">

<!-- In-place comment submission -->
<form hx-post="{% url 'central_admin:bus_request_comment' %}" 
      hx-target="#comment-section-{{id}}" 
      hx-swap="beforeend">
```

**HTMX Swap Strategies**: Use `beforeend` for appending (comments), `innerHTML` for replacing (filters), `outerHTML` for full updates

### SCSS Architecture
**Modular structure** in `src/static/styles/`:
```
styles/
  ├─ base/
  │   ├─ _colors.scss (Tailwind-inspired palette: $indigo-600, $gray-700, etc.)
  │   ├─ _typography.scss
  │   ├─ _buttons.scss
  │   └─ _input.scss
  ├─ {role}/               (central_admin, institution_admin, students)
  │   └─ {page}/           (dashboard, login_page, etc.)
  │       ├─ style.scss    (SCSS source - edit this)
  │       └─ style.css     (auto-generated - DO NOT edit)
  ├─ _base.scss            (imports base partials)
  └─ _sidebar_navbar_base.scss (layout components)
```

**Important**: CSS files are **auto-generated** from SCSS. Only edit `.scss` files - never manually edit `.css` files.

**Color System**: Use Tailwind CSS color variables (`$indigo-50` through `$indigo-950` for primary, `$gray-*` for neutrals)

**Active State Pattern**:
```html
<!-- Sidebar uses Django template logic for active class -->
<a href="{% url 'central_admin:dashboard' %}" 
   class="navlink {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}">
```

### JavaScript Conventions
- **Vanilla JS only** - no frameworks (React/Vue/Angular)
- **Client-side validation** - `bus_booking.js` example: adds `.is-invalid` class + error messages
- **Bootstrap 5 components** - dropdowns, modals, tooltips via `bootstrap.bundle.min.js`
- **Font Awesome** icons for UI elements

### Static File Organization
```
static/
  ├─ images/ (logo.svg, profile-default-icon.jpg)
  ├─ js/ (bus_booking.js - form validation helpers)
  ├─ styles/ (SCSS source files)
  └─ utils/
      ├─ bootstrap/ (Bootstrap 5 CSS/JS)
      ├─ htmx/ (htmx.min.js)
      └─ font_awesome/
```

**Static File Loading**:
- Development: WhiteNoise serves from `static/` + `staticfiles/` (auto-collected via `collectstatic`)
- Production: DigitalOcean Spaces CDN

### Common UI Patterns
1. **Tables**: Use `.table-responsive` wrapper, all cells have `padding: 1rem`, `white-space: nowrap`
2. **Cards**: Sidebar statistics use `.card` with flexbox layout
3. **Forms**: Bootstrap form classes (`.form-label`, `.form-select`, `.form-control`)
4. **Notifications**: Priority notifications auto-load via HTMX, dismissible with `hx-get` mark-as-read
5. **Partials**: Reusable components in `templates/{role}/partials/` (e.g., `student_group_options.html`)

## Adding New Features

1. **New Model**: Add to appropriate `services/models/{category}.py` → include `org`, `slug`, docstrings → export in `services/models/__init__.py`
2. **New Admin View**: Create in `services/views/{role}.py` → add URL in `services/urls/{role}.py` → use appropriate access mixin
3. **New Async Task**: Add to `services/tasks.py` → create/update `Notification` for user feedback
4. **New Form**: Add to `services/forms/{role}.py` → use Bootstrap classes for styling
5. **New Template**: Extend `base.html` → include role-specific sidebar → add to `templates/{role}/`
6. **New SCSS**: Create `style.scss` in `static/styles/{role}/{page}/` → import base partials → CSS auto-compiles
7. **Access Control**: Always use mixins from `config/mixins/access_mixin.py` for role-based views
8. **Always**: Write tests in `services/test/test_models.py` or `core/test/`, run before committing

## Testing Strategy

Tests in `services/test/test_models.py` - focus on model validation, slug generation, signal handlers

**Run Frequently**: Tests use `config.test_settings.py` with in-memory DB for speed

---

**Timezone**: All timestamps in `Asia/Kolkata` (`USE_TZ=True`)  
**Auth**: Custom user model - use `get_user_model()`, not `User` directly  
**Logging**: Production uses file logging (`debug.log`) + console - check `LOGGING` config in settings
