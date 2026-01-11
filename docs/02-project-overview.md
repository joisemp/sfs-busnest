# Project Overview

## What is SFS BusNest?

SFS BusNest is a comprehensive bus management system designed for managing student transportation across multiple educational institutions. It provides a centralized platform for bus seat allocation, route planning, automated booking, and operational management.

## Purpose

The system addresses the complexity of managing shared bus services across multiple schools, colleges, and educational institutions within a single organization. It streamlines:

- Student registration and seat allocation
- Route and schedule management
- Payment and receipt tracking
- Bus reservation requests
- Refueling and maintenance records
- Real-time notifications and reporting

## Key Features

### 1. Multi-Tenancy

- **Organization-Level Isolation**: Each organization operates independently
- **Institution Management**: Multiple institutions per organization
- **Shared Resources**: Buses and routes shared across institutions
- **Centralized Control**: Single admin dashboard for the entire organization

### 2. Role-Based Access Control

Four distinct user roles with separate dashboards:

- **Central Admin**: Full system access, manages all institutions
- **Institution Admin**: Manages their institution's students and bookings
- **Driver**: Views assigned trips, manages refueling records
- **Student**: Views tickets, schedules, and makes bookings

### 3. Registration Management

- **Booking Periods**: Time-bound registration events
- **Unique Registration Codes**: Shareable codes for student access
- **Schedule Groups**: Flexible pickup/drop combinations
- **Capacity Management**: Automatic seat availability tracking

### 4. Route & Schedule Planning

- **Dynamic Route Creation**: Create and modify routes with multiple stops
- **Stop Management**: Drag-and-drop interface for stop transfers
- **Schedule Configuration**: Morning, evening, or custom schedules
- **Trip Generation**: Automatic trip creation from routes + schedules + buses

### 5. Automated Booking System

- **Receipt Validation**: Students must have valid receipts to book
- **Seat Allocation**: Real-time capacity checking
- **Bus Assignment**: Automatic assignment to appropriate bus records
- **Trip Selection**: Students choose pickup and drop schedules

### 6. Payment & Receipt Tracking

- **Excel Import**: Bulk receipt upload from Excel files
- **Payment Installments**: Track multiple payment dates
- **Receipt Expiration**: Time-based receipt validity
- **Validation**: Automatic student ID matching

### 7. Bus Reservation System

- **Institution Requests**: Request buses for special events
- **Assignment Management**: Allocate buses to requests
- **Trip Expenses**: Track costs per reservation trip
- **Approval Workflow**: Request, assignment, and confirmation

### 8. Driver Features

- **Assigned Trips**: View daily trip assignments
- **Refueling Records**: Log fuel consumption and costs
- **Odometer Tracking**: Maintain vehicle mileage records
- **Dashboard**: Quick access to important information

### 9. Background Processing

- **Excel Processing**: Asynchronous file uploads (routes, receipts, buses)
- **Email Notifications**: Queued email sending
- **Scheduled Tasks**: Automatic receipt expiration marking
- **Report Generation**: Async ticket exports and student passes

### 10. Reporting & Analytics

- **Ticket Exports**: Excel exports of bookings
- **Student Passes**: Automated pass generation
- **Activity Logs**: Complete audit trail
- **Usage Statistics**: Dashboard metrics and charts

## Technology Stack

### Backend
- **Framework**: Django 5.x
- **Language**: Python 3.12+
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis
- **Task Queue**: Celery with Beat scheduler
- **Task Monitor**: Flower

### Frontend
- **Templates**: Django Templates
- **CSS Framework**: Bootstrap 5
- **Styling**: SCSS (compiled to CSS)
- **JavaScript**: Vanilla JS (no frameworks)
- **Dynamic Updates**: HTMX
- **Icons**: Font Awesome

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Static Files**: WhiteNoise (dev), S3-compatible storage (prod)
- **File Storage**: Local (dev), DigitalOcean Spaces (prod)
- **Email**: Console backend (dev), Mailjet SMTP (prod)

## System Capabilities

### Multi-Institution Support
```
Organization
  ├─ Institution A (500 students)
  ├─ Institution B (300 students)
  └─ Institution C (200 students)

Shared Resources:
  ├─ 20 Buses (organization fleet)
  ├─ 15 Routes
  └─ 1 Active Registration
```

### Scalability
- Supports unlimited organizations
- Handles thousands of students per registration
- Manages hundreds of buses and routes
- Processes bulk operations asynchronously

### Performance
- Redis caching for session management
- Asynchronous task processing with Celery
- Optimized database queries with select_related/prefetch_related
- Static file CDN in production

## User Workflows

### Central Admin Workflow
1. Create organization and institutions
2. Upload bus fleet and routes via Excel
3. Create registration with schedule groups
4. Upload receipts for student validation
5. Generate trips (route + schedule + bus)
6. Monitor bookings and manage assignments
7. Handle bus reservation requests
8. Export reports and analytics

### Institution Admin Workflow
1. View institution's student groups
2. Request buses for special events
3. Monitor student bookings
4. Generate institution-specific reports
5. Manage student information

### Driver Workflow
1. View assigned trips and schedules
2. Log refueling records
3. Track odometer readings
4. Access route and stop information

### Student Workflow
1. Access registration with unique code
2. Select pickup and drop schedules
3. Choose preferred routes and stops
4. Confirm booking and seat allocation
5. View ticket and bus information
6. Download student pass

## Business Rules

### Registration
- Only one registration can be active at a time
- Registrations have start and end dates
- Unique codes enable student access

### Booking
- Students need valid, non-expired receipts
- Receipt student_id must match the booking student_id
- Seats allocated based on trip capacity
- No overbooking (enforced at trip level)

### Capacity
- `Trip.booking_count` tracks current bookings
- `BusRecord.min_required_capacity` auto-calculated
- Capacity checked before allowing bookings
- Real-time availability display

### Payments
- Multiple installment dates per ticket
- Payment tracking separate from tickets
- Receipt validation before booking

### Stop Transfers
- Moving stops updates all associated tickets
- Selective bus record updates (pickup vs drop)
- Trip booking counts recalculated
- Route-specific validation

## Data Flow

### Student Booking Flow
```
Student enters Registration Code
  ↓
System validates Receipt (student_id, expiration)
  ↓
Student selects Schedule Group (pickup/drop)
  ↓
Student selects Routes and Stops
  ↓
System finds valid Trips (route + schedule + bus)
  ↓
System checks capacity (booking_count < bus capacity)
  ↓
Creates Ticket with Bus Record assignments
  ↓
Increments Trip.booking_count
  ↓
Sends confirmation notification
```

### Excel Import Flow
```
Admin uploads Excel file
  ↓
System validates file format
  ↓
Creates background Celery task
  ↓
Creates notification (status: pending)
  ↓
Task processes file row-by-row
  ↓
Creates/updates database records
  ↓
Updates notification (status: completed/error)
  ↓
Admin receives notification
```

## Security Features

- **Multi-Tenancy**: Organization-level data isolation
- **Role-Based Access**: Strict permission enforcement
- **CSRF Protection**: Django CSRF tokens
- **XSS Prevention**: Template auto-escaping
- **SQL Injection**: Django ORM parameterized queries
- **File Upload Validation**: Type and size restrictions
- **Authentication**: Session-based with secure cookies

## Integration Points

### Email
- Celery tasks for async sending
- Template-based emails
- Mailjet SMTP (production)

### File Storage
- Local storage (development)
- S3-compatible storage (production)
- Automatic file naming and organization

### Reporting
- Excel exports via openpyxl
- PDF generation for student passes
- CSV exports for data analysis

## Future Enhancements

Potential areas for expansion:
- Mobile app (iOS/Android)
- Real-time GPS tracking
- Parent portal
- SMS notifications
- Payment gateway integration
- Advanced analytics dashboard
- Maintenance scheduling
- Fuel efficiency reports
- Driver performance metrics

## Next Steps

- **For Developers**: Read [System Architecture](./03-architecture.md)
- **For Database Design**: Study [Data Models](./04-data-models.md)
- **For Access Control**: Review [User Roles & Permissions](./05-roles-permissions.md)
