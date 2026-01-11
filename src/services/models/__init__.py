"""
Django models for the services app.

This module is now organized into separate files for better maintainability:
- core.py: Organisation, Institution
- routes.py: Route, Stop, RouteFile
- registrations.py: Registration, Schedule, ScheduleGroup
- buses.py: Bus, RefuelingRecord, BusFile
- bus_operations.py: BusRecord, Trip
- tickets.py: Ticket, InstallmentDate, Payment, StudentGroup, Receipt, ReceiptFile
- requests.py: FAQ, BusRequest, BusRequestComment
- reservations.py: BusReservationRequest, BusReservationAssignment, TripExpense
- system.py: ExportedFile, UserActivity, Notification, StudentPassFile
- utils.py: Utility functions (rename_*, log_user_activity)

All models are imported here to maintain backward compatibility with existing code.
"""

# Core models
from .core import (
    Organisation,
    Institution,
)

# Route models
from .routes import (
    Route,
    Stop,
    RouteFile,
)

# Registration and schedule models
from .registrations import (
    Registration,
    Schedule,
    ScheduleGroup,
)

# Bus models
from .buses import (
    Bus,
    RefuelingRecord,
    BusFile,
)

# Bus operations models
from .bus_operations import (
    BusRecord,
    Trip,
)

# Ticket and payment models
from .tickets import (
    Ticket,
    InstallmentDate,
    Payment,
    StudentGroup,
    Receipt,
    ReceiptFile,
)

# Request models
from .requests import (
    FAQ,
    BusRequest,
    BusRequestComment,
)

# Reservation models
from .reservations import (
    BusReservationRequest,
    BusReservationAssignment,
    TripExpense,
)

# System models
from .system import (
    ExportedFile,
    UserActivity,
    Notification,
    StudentPassFile,
)

# Utility functions
from .utils import (
    rename_uploaded_file,
    rename_bus_uploaded_file,
    rename_exported_file,
    rename_student_pass_file,
    rename_uploaded_file_receipt,
    log_user_activity,
)

# Export all models and utilities
__all__ = [
    # Core
    'Organisation',
    'Institution',
    # Routes
    'Route',
    'Stop',
    'RouteFile',
    # Registrations
    'Registration',
    'Schedule',
    'ScheduleGroup',
    # Buses
    'Bus',
    'RefuelingRecord',
    'BusFile',
    # Bus Operations
    'BusRecord',
    'Trip',
    # Tickets and Payments
    'Ticket',
    'InstallmentDate',
    'Payment',
    'StudentGroup',
    'Receipt',
    'ReceiptFile',
    # Requests
    'FAQ',
    'BusRequest',
    'BusRequestComment',
    # Reservations
    'BusReservationRequest',
    'BusReservationAssignment',
    'TripExpense',
    # System
    'ExportedFile',
    'UserActivity',
    'Notification',
    'StudentPassFile',
    # Utilities
    'rename_uploaded_file',
    'rename_bus_uploaded_file',
    'rename_exported_file',
    'rename_student_pass_file',
    'rename_uploaded_file_receipt',
    'log_user_activity',
]
