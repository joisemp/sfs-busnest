# SFS BusNest - AI Coding Agent Instructions

## Project Overview
SFS BusNest is a Django-based centralized bus management system for multiple educational institutions. It manages student registration, bus seat allocation, route planning, and automated booking across shared bus services.

**Key Design Principle**: Multi-tenancy at the organization level with role-based access (Central Admin, Institution Admin, Students).

## Architecture

### Core Components
- **`core/`**: Custom user authentication (`User` with email as USERNAME_FIELD, `UserProfile` with role flags)
- **`services/`**: Main business logic - 25+ models covering organisations, institutions, routes, buses, tickets, receipts, notifications
- **`config/`**: Settings, Celery config, middleware (maintenance mode), validators, utils

### User Roles & Access Pattern
```python
# Three distinct user types with separate URL namespaces
UserProfile.is_central_admin    # Full system access - manages all institutions
UserProfile.is_institution_admin # Institution-scoped - manages their institution only
UserProfile.is_student          # Read-only access - views their tickets/schedules
```

**URL Structure**: `/central_admin/`, `/institution_admin/`, `/students/` - each with separate views/forms/urls modules in `services/`

### Data Hierarchy
```
Organisation (org)
  ├─ Institution(s)
  │   ├─ StudentGroup(s) (class-section combinations)
  │   └─ UserProfile(s) (institution admins)
  ├─ Registration (booking period/event)
  │   ├─ Route(s) → Stop(s)
  │   ├─ Schedule(s) (morning/evening timings)
  │   ├─ ScheduleGroup(s) (pickup+drop pairs)
  │   ├─ BusRecord(s) (bus assigned to registration)
  │   │   └─ Trip(s) (route+schedule+bus combination)
  │   ├─ Receipt(s) (payment validation)
  │   └─ Ticket(s) (student bookings)
  └─ Bus(es) (organization fleet)
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
1. **Unique Slugs**: All models use `slug = SlugField(unique=True, db_index=True)` with auto-generation in `save()` via `config.utils.generate_unique_slug()`
2. **Unique Codes**: Registration uses `generate_unique_code()` for shareable booking codes
3. **Organisation Scoping**: Always filter by `org=request.user.profile.org` in views
4. **Soft Deletes**: Use `is_available` (Bus), `is_expired` (Receipt), `status` (Ticket) instead of hard deletes
5. **Signals**: `Ticket` deletion auto-decrements `Trip.booking_count` via `update_trip_booking_count_on_ticket_delete` signal

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

### Form Handling
Forms split by role: `services/forms/{central_admin,institution_admin,students}.py`

**HTMX Integration**: Many forms use HTMX for dynamic updates (check templates for `hx-` attributes)

### Static Files
- **Development**: WhiteNoise serves from `src/static/` and `src/staticfiles/`
- **Production**: DigitalOcean Spaces (S3-compatible) via `django-storages`
- **Technologies**: Bootstrap 5, SCSS, vanilla JS, HTMX (no React/Vue)

## Common Gotchas

1. **Trip Booking Count**: Must manually increment/decrement `Trip.booking_count` when creating/deleting tickets
2. **BusRecord.min_required_capacity**: Auto-calculated on save based on max `Trip.booking_count` - don't set manually
3. **Receipt Validation**: Students need valid non-expired `Receipt` matching their `student_id` before booking
4. **Schedule Groups**: `allow_one_way` flag determines if students can book only pickup or drop
5. **Student Group Format**: Always `"{CLASS} - {SECTION}"` (e.g., "5 - A"), case-insensitive in Excel processing
6. **File Storage**: Use `default_storage.open()` for cloud compatibility in Celery tasks

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
**Three-layer base template inheritance**:
```
base.html (global layout)
  ├─ central_admin/ (extends base.html)
  ├─ institution_admin/ (extends base.html)
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

1. **New Model**: Add to `services/models.py` → include `org`, `slug`, docstrings
2. **New Admin View**: Create in `services/views/central_admin.py` → add URL in `services/urls/central_admin.py`
3. **New Async Task**: Add to `services/tasks.py` → create/update `Notification` for user feedback
4. **New Form**: Add to `services/forms/{role}.py` → use Bootstrap classes for styling
5. **New Template**: Extend `base.html` → include role-specific sidebar → add to `templates/{role}/`
6. **New SCSS**: Create `style.scss` in `static/styles/{role}/{page}/` → import base partials → CSS auto-compiles
7. **Always**: Write tests in `services/test/`, run before committing

## Testing Strategy

Tests in `services/test/test_models.py` - focus on model validation, slug generation, signal handlers

**Run Frequently**: Tests use `config.test_settings.py` with in-memory DB for speed

---

**Timezone**: All timestamps in `Asia/Kolkata` (`USE_TZ=True`)  
**Auth**: Custom user model - use `get_user_model()`, not `User` directly  
**Logging**: Production uses file logging (`debug.log`) + console - check `LOGGING` config in settings
