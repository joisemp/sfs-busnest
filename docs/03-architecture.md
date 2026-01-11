# System Architecture

This document provides a comprehensive overview of the SFS BusNest system architecture, component interactions, and design decisions.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer / Reverse Proxy            │
│                     (Nginx - Production)                     │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
┌───────▼────────┐                      ┌────────▼─────────┐
│  Django App    │                      │  Static Files    │
│  (Gunicorn)    │                      │  (CDN/S3)        │
│                │                      │                  │
│  - Views       │                      │  - CSS/JS        │
│  - Forms       │                      │  - Images        │
│  - Models      │                      │  - Uploads       │
└────┬─────┬─────┘                      └──────────────────┘
     │     │
     │     └────────────────┐
     │                      │
┌────▼────────┐      ┌──────▼──────┐        ┌──────────────┐
│ PostgreSQL  │      │   Redis     │        │   Celery     │
│             │      │             │        │   Workers    │
│  - Tables   │      │  - Cache    │◄───────┤              │
│  - Indexes  │      │  - Sessions │        │  - Tasks     │
│  - Relations│      │  - Queue    │        │  - Beat      │
└─────────────┘      └─────────────┘        │  - Flower    │
                                             └──────────────┘
```

## Application Layers

### 1. Presentation Layer (Frontend)

**Location**: `src/templates/`, `src/static/`

#### Components:
- **Django Templates**: Server-side rendered HTML
- **Bootstrap 5**: Responsive UI framework
- **SCSS**: Modular styling with compilation
- **HTMX**: Dynamic page updates without full reload
- **Vanilla JavaScript**: Client-side interactions

#### Organization:
```
templates/
├── base.html                    # Global layout
├── central_admin/               # Central admin templates
├── institution_admin/           # Institution admin templates
├── drivers/                     # Driver templates
├── students/                    # Student templates
└── core/                        # Auth templates

static/
├── styles/                      # SCSS source files
│   ├── base/                   # Shared styles
│   └── {role}/                 # Role-specific styles
├── js/                         # JavaScript files
├── images/                     # Static images
└── utils/                      # Third-party libraries
```

### 2. Application Layer (Backend)

**Location**: `src/services/`, `src/core/`, `src/config/`

#### Core Components:

**A. Views (`services/views/`)**
- Role-based view organization
- Class-based views (CBVs) for consistency
- Mixins for access control
- API views for AJAX operations

**B. Forms (`services/forms/`)**
- Django forms for validation
- Role-specific form files
- Custom validators
- HTMX integration

**C. Models (`services/models/`)**
- Modular organization (10 files)
- Multi-tenancy via `org` field
- Automatic slug generation
- Signal handlers

**D. URL Routing (`services/urls/`)**
- Role-based namespaces
- RESTful patterns
- Slug-based URLs

**E. Business Logic (`services/utils/`)**
- Transfer stop utility
- Helper functions
- Custom decorators

**F. Background Tasks (`services/tasks.py`)**
- Excel processing
- Email sending
- Report generation
- Scheduled jobs

### 3. Data Layer

**Location**: PostgreSQL database

#### Key Design Patterns:
- **Multi-tenancy**: All models have `org` ForeignKey
- **Soft Deletes**: Status fields instead of hard deletes
- **Audit Trail**: UserActivity model logs all actions
- **Normalized Schema**: Third normal form (3NF)

### 4. Cache Layer

**Location**: Redis

#### Usage:
- Session storage
- Celery task queue
- Celery results backend
- Rate limiting (future)

### 5. Task Queue Layer

**Location**: Celery workers

#### Components:
- **Worker**: Executes async tasks
- **Beat**: Schedules periodic tasks
- **Flower**: Monitoring interface

## Component Interactions

### Request-Response Flow

```
1. User Request
   ↓
2. Django URL Resolver
   ↓
3. View (with Access Mixin)
   ↓
4. Authentication Check
   ↓
5. Organization Filter (Multi-tenancy)
   ↓
6. Business Logic
   ↓
7. Database Query (PostgreSQL)
   ↓
8. Template Rendering
   ↓
9. HTTP Response
```

### Asynchronous Task Flow

```
1. User uploads Excel file
   ↓
2. View validates file
   ↓
3. View creates Celery task
   ↓
4. Task queued in Redis
   ↓
5. Celery worker picks up task
   ↓
6. Task processes file
   ↓
7. Task updates database
   ↓
8. Task creates notification
   ↓
9. User sees notification in UI
```

### HTMX Dynamic Update Flow

```
1. User action (click, change)
   ↓
2. HTMX sends AJAX request
   ↓
3. Django view processes request
   ↓
4. View returns HTML fragment
   ↓
5. HTMX swaps content in DOM
   ↓
6. No full page reload
```

## Module Structure

### Core App (`core/`)

**Purpose**: User authentication and profile management

```
core/
├── models.py              # User, UserProfile
├── views.py               # Login, logout, profile
├── forms.py               # Auth forms
├── urls.py                # Auth URLs
├── user_manager.py        # Custom user manager
└── test/                  # Core tests
```

### Services App (`services/`)

**Purpose**: Main business logic

```
services/
├── models/
│   ├── core.py           # Organisation, Institution
│   ├── routes.py         # Route, Stop, RouteFile
│   ├── registrations.py  # Registration, Schedule
│   ├── buses.py          # Bus, RefuelingRecord
│   ├── bus_operations.py # BusRecord, Trip
│   ├── tickets.py        # Ticket, Payment
│   ├── requests.py       # BusRequest, FAQ
│   ├── reservations.py   # BusReservationRequest
│   ├── system.py         # Notification, UserActivity
│   └── utils.py          # Utility functions
├── views/
│   ├── central_admin.py  # Central admin views
│   ├── institution_admin.py
│   ├── drivers.py
│   └── students.py
├── forms/                # Role-based forms
├── urls/                 # Role-based URLs
├── utils/                # Business logic utilities
├── tasks.py              # Celery tasks
└── admin.py              # Django admin customization
```

### Config App (`config/`)

**Purpose**: Django configuration

```
config/
├── settings.py           # Main settings
├── test_settings.py      # Test configuration
├── celery.py            # Celery configuration
├── urls.py              # Root URL routing
├── utils.py             # Helper functions
├── validators.py        # Custom validators
├── middleware/          # Custom middleware
│   └── maintenance.py   # Maintenance mode
└── mixins/              # Access control mixins
    └── access_mixin.py
```

## Design Patterns

### 1. Multi-Tenancy Pattern

**Implementation**: Organization-level isolation

```python
# All queries filtered by organization
queryset = Model.objects.filter(org=request.user.profile.org)

# All models have org field
class SomeModel(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE)
```

### 2. Role-Based Access Control

**Implementation**: Mixin-based access control

```python
# Access mixins enforce role checks
class SomeView(CentralAdminOnlyAccessMixin, ListView):
    def get_queryset(self):
        return Model.objects.filter(org=self.request.user.profile.org)
```

### 3. Repository Pattern

**Implementation**: Modular model organization

```python
# Models split across logical files
from services.models import Route, Stop  # Imports from __init__.py
```

### 4. Observer Pattern

**Implementation**: Django signals

```python
# Automatic trip count updates
@receiver(post_delete, sender=Ticket)
def update_trip_booking_count_on_ticket_delete(sender, instance, **kwargs):
    # Update trip counts
```

### 5. Factory Pattern

**Implementation**: Model creation utilities

```python
# Trip generation from routes + schedules + buses
def generate_trips(registration):
    for route in routes:
        for schedule in schedules:
            for bus_record in bus_records:
                Trip.objects.create(...)
```

### 6. Strategy Pattern

**Implementation**: Role-based views

```python
# Different views for different roles
/central_admin/dashboard/  → CentralAdminDashboardView
/drivers/dashboard/        → DriverDashboardView
/students/dashboard/       → StudentDashboardView
```

## Security Architecture

### 1. Authentication
- Django session-based authentication
- Email as username
- Password hashing (PBKDF2)

### 2. Authorization
- Role-based access via UserProfile.role
- Access mixins on all views
- Organization-level isolation

### 3. CSRF Protection
- Django CSRF middleware enabled
- Tokens in all forms
- AJAX requests include CSRF header

### 4. XSS Protection
- Template auto-escaping enabled
- Safe string marking where needed
- Content Security Policy (production)

### 5. SQL Injection Prevention
- Django ORM parameterized queries
- No raw SQL without escaping
- Query validation

### 6. File Upload Security
- Type validation (Excel only for imports)
- Size limits enforced
- Filename sanitization
- Separate storage from static files

## Scalability Considerations

### Horizontal Scaling
- Stateless Django application
- Session data in Redis
- Static files on CDN
- Multiple Celery workers

### Vertical Scaling
- PostgreSQL connection pooling
- Redis as cache layer
- Optimized database queries
- Background task processing

### Database Optimization
- Indexes on slugs and foreign keys
- select_related for single joins
- prefetch_related for multiple joins
- Database query monitoring

### Caching Strategy
- Redis for session data
- Static files with cache headers
- Database query caching (future)

## Deployment Architecture

### Development
```
Docker Compose
├── Django (runserver)
├── PostgreSQL
├── Redis
├── Celery Worker
├── Celery Beat
└── Flower
```

### Production
```
Load Balancer
├── Gunicorn Workers (multiple)
│   └── Django App
├── PostgreSQL (managed service)
├── Redis (managed service)
├── Celery Workers (autoscaling)
├── Celery Beat (singleton)
└── CDN (static files)
```

## Monitoring & Logging

### Application Logs
- Django logging framework
- File-based logs (production)
- Console logs (development)

### Task Monitoring
- Flower web interface
- Task success/failure tracking
- Performance metrics

### Database Monitoring
- PostgreSQL logs
- Query performance tracking
- Connection pool monitoring

### Error Tracking
- Django error emails (production)
- Log aggregation (future)
- APM tools (future)

## Data Flow Diagrams

### Student Booking Flow
```
┌─────────┐      ┌──────────┐      ┌─────────┐      ┌────────┐
│ Student │──1──▶│ Receipt  │──2──▶│ Ticket  │──3──▶│  Trip  │
└─────────┘      │Validation│      │ Creation│      │ Update │
                 └──────────┘      └─────────┘      └────────┘
                      │                  │                │
                      │                  │                │
                   Checks:          Creates:         Updates:
                   - Valid         - Ticket         - booking_count
                   - Not expired   - Payments       - min_capacity
                   - Matches ID    - Assignments
```

### Excel Import Flow
```
┌──────┐    ┌─────────┐    ┌────────┐    ┌──────────┐
│ Admin│───▶│ Upload  │───▶│ Celery │───▶│ Database │
└──────┘    │Validate │    │  Task  │    │  Update  │
            └─────────┘    └────────┘    └──────────┘
                 │              │              │
                 │              │              │
            Validates:     Processes:     Creates:
            - File type   - Row by row   - Models
            - File size   - Error handle - Notification
            - Format      - Logging
```

## Technology Choices

### Why Django?
- Mature ORM for complex relationships
- Built-in admin interface
- Excellent security features
- Large ecosystem
- Python ecosystem integration

### Why PostgreSQL?
- ACID compliance
- Complex query support
- Excellent Django integration
- Proven scalability
- JSON field support

### Why Redis?
- Fast session storage
- Celery backend
- Simple caching
- Pub/sub for future features

### Why Celery?
- Async task processing
- Periodic task scheduling
- Result tracking
- Retry mechanisms

### Why Bootstrap?
- Rapid UI development
- Responsive by default
- Large component library
- Community support

### Why HTMX?
- Progressive enhancement
- Minimal JavaScript
- Server-side rendering
- Easy integration

## Next Steps

- **Data Models**: See [Data Models](./04-data-models.md)
- **Permissions**: Review [User Roles & Permissions](./05-roles-permissions.md)
- **Backend Development**: Read [Backend Development](./06-backend-development.md)
