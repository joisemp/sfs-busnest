"""
Django models for the services app.

This module defines the database schema for the SFS Institutions system, including organizations, institutions, routes, stops, registrations, schedules, buses, bus records, trips, tickets, student groups, receipts, files, FAQs, bus requests, notifications, and user activity logging.

Each model includes field definitions, relationships, and custom save logic where needed. Utility functions for file renaming and a signal for updating trip booking counts on ticket deletion are also provided.

Models:
    Organisation: Represents an organization (e.g., a school group or company).
    Institution: Represents an institution under an organization.
    Route: Represents a bus route.
    Stop: Represents a stop on a route.
    RouteFile: File uploads for route data.
    Registration: Represents a registration event or period.
    Schedule: Represents a schedule (e.g., morning, evening).
    ScheduleGroup: Groups pickup and drop schedules.
    Bus: Represents a bus.
    BusRecord: Represents a bus assigned to a registration.
    Trip: Represents a trip for a bus record and schedule.
    Ticket: Represents a student's bus ticket.
    StudentGroup: Represents a group/class of students.
    Receipt: Represents a payment receipt for a student.
    ReceiptFile: File uploads for receipt data.
    FAQ: Frequently asked questions for a registration.
    BusRequest: Student bus requests.
    BusRequestComment: Comments on bus requests.
    ExportedFile: Files exported by users.
    BusFile: File uploads for bus data.
    UserActivity: Logs user actions.
    Notification: User notifications.
    StudentPassFile: File uploads for student passes.

Utility Functions:
    rename_uploaded_file, rename_bus_uploaded_file, rename_exported_file, rename_student_pass_file, rename_uploaded_file_receipt: Custom file path generators for uploads.
    log_user_activity: Helper to log user actions.

Signals:
    update_trip_booking_count_on_ticket_delete: Updates trip booking counts when a ticket is deleted.
"""

import os
from uuid import uuid4
from django.db import models
from django.forms import ValidationError
from django.utils.text import slugify
from django.core.validators import RegexValidator
from config.validators import validate_excel_file
from config.utils import generate_unique_slug, generate_unique_code
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver

class Organisation(models.Model):
    """
    Represents an organization, such as a school group or company.
    Fields:
        name, contact_no, email, area, city, slug, created_at, updated_at
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the organization name.
    """
    name = models.CharField(max_length=200, db_index=True)
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
        db_index=True,
        null=True
    )
    email = models.EmailField(unique=True, db_index=True, null=True)
    area = models.CharField(max_length=200)
    city = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Save the Organisation instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String representation of the Organisation.
        """
        return f"{self.name}"

class Institution(models.Model):
    """
    Represents an institution under an organization.
    Fields:
        org, name, label, contact_no, email, slug, incharge, created_at, updated_at
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the institution name and label.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='institutions')
    name = models.CharField(max_length=200, db_index=True)
    label = models.CharField(max_length=50, unique=True)
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
        db_index=True
    )
    email = models.EmailField(unique=True, db_index=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    incharge = models.OneToOneField('core.UserProfile', max_length=200, null=True, on_delete=models.SET_NULL, related_name='institution')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Save the Institution instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String representation of the Institution.
        """
        return f"{self.name} - {self.label}"

class Route(models.Model):
    """
    Represents a bus route for an organization and registration.
    Fields:
        org, registration, name, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the route name.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='routes')
    registration = models.ForeignKey('services.Registration', on_delete=models.CASCADE, related_name='routes')
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the Route instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        """
        String representation of the Route.
        """
        return f"{self.name}"

class Stop(models.Model):
    """
    Represents a stop on a route for a registration.
    Fields:
        org, registration, route, name, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the stop name.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='stops')
    registration = models.ForeignKey('services.Registration', on_delete=models.CASCADE, related_name='stops')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    
    def save(self, *args, **kwargs):
        """
        Save the Stop instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        """
        String representation of the Stop.
        """
        return f"{self.name}"
    
def rename_uploaded_file(instance, filename):
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/route_files/{slugify(base_name)}-{uuid4()}{ext}"

def rename_bus_uploaded_file(instance, filename):
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/bus_files/{slugify(base_name)}-{uuid4()}{ext}"

def rename_exported_file(instance, filename):
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.user.profile.org.slug}/exported_files/{slugify(base_name)}-{uuid4()}{ext}"

def rename_student_pass_file(instance, filename):
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.user.profile.org.slug}/student_pass/{slugify(base_name)}-{uuid4()}{ext}"

class RouteFile(models.Model):
    """
    Represents a file upload for route data.
    Fields:
        org, name, file, added, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the file name.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='route_files')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to=rename_uploaded_file, validators=[validate_excel_file])
    added = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the RouteFile instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        """
        String representation of the RouteFile.
        """
        return f"{self.name}"

class Registration(models.Model):
    """
    Represents a registration event or period for an organization.
    Fields:
        org, name, instructions, status, code, slug
    Methods:
        save: Generates a unique slug and code if not present.
        __str__: Returns the registration name.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='registrations')
    name = models.CharField(max_length=200)
    instructions = models.TextField()
    status = models.BooleanField(default=False)
    code = models.CharField(max_length=100, unique=True, null=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the Registration instance, generating a unique slug and code if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        if not self.code:
            self.code = generate_unique_code(self, unique_field='code')
        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        String representation of the Registration.
        """
        return f"{self.org}{self.name}"

class Schedule(models.Model):
    """
    Represents a schedule (e.g., morning, evening) for a registration.
    Fields:
        org, registration, name, start_time, end_time, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the schedule name and time range.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='schedules')
    registration = models.ForeignKey('services.Registration', on_delete=models.CASCADE, related_name='schedules')
    name = models.CharField(max_length=50)  # Example: "Morning", "Afternoon", "Evening"
    start_time = models.TimeField()  # Example: 08:00 AM
    end_time = models.TimeField()    # Example: 11:00 AM
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the Schedule instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String representation of the Schedule.
        """
        return f"{self.name} ({self.start_time} - {self.end_time})"

class ScheduleGroup(models.Model):
    """
    Groups pickup and drop schedules for a registration.
    Fields:
        registration, pick_up_schedule, drop_schedule, allow_one_way, description
    Methods:
        __str__: Returns a string representation of the group.
    """
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='schedule_groups')
    pick_up_schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='pickup_groups')
    drop_schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='drop_groups')
    allow_one_way = models.BooleanField(default=False)
    description = models.CharField(max_length=500)
    
    def __str__(self):
        """
        String representation of the ScheduleGroup.
        """
        return f"{self.pick_up_schedule.name}-{self.drop_schedule.name}"

class Bus(models.Model):
    """
    Represents a bus belonging to an organization.
    Fields:
        org, registration_no, driver, capacity, is_available, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the bus registration number and capacity.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='buses')
    registration_no = models.CharField(max_length=100)
    driver = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField(blank=False, null=False)
    is_available = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the Bus instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"bus-{self.registration_no}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String representation of the Bus.
        """
        return f"{self.registration_no} (Capacity : {self.capacity})"

class BusRecord(models.Model):
    """
    Represents a bus assigned to a registration.
    Fields:
        org, bus, registration, label, min_required_capacity, slug
    Methods:
        clean: Validates minimum required capacity.
        save: Generates a unique slug, updates label and min_required_capacity.
        __str__: Returns the label.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='bus_records')
    bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, blank=True, related_name='records')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='bus_records')
    label = models.CharField(max_length=20)
    min_required_capacity = models.PositiveIntegerField(default=0)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    class Meta:
        unique_together = ('bus', 'registration')
        
    def clean(self):
        """
        Validates that min_required_capacity does not exceed bus capacity.
        """
        if self.bus:
            if self.min_required_capacity > self.bus.capacity:
                raise ValidationError(
                    f"The bus capacity ({self.bus.capacity}) is less than the minimum capacity of ({self.min_required_capacity})."
                )

    def save(self, *args, **kwargs):
        """
        Save the BusRecord instance, generating a unique slug and updating label/capacity.
        """
        if not self.slug:
            base_slug = slugify(f"record-{self.bus.registration_no}-{self.registration.name}")
            self.slug = generate_unique_slug(self, base_slug)
        
        # Ensure label is saved in title case
        self.label = self.label.title()
        
        super().save(*args, **kwargs)  # Save the instance to ensure it has a primary key
        
        # calculate minimum required capacity
        related_trips = self.trips.all()
        if related_trips.exists():
            self.min_required_capacity = max(trip.booking_count for trip in related_trips)
        
        super().save(*args, **kwargs)  # Save again to update min_required_capacity

    def __str__(self):
        """
        String representation of the BusRecord.
        """
        return f"{self.label}"

class Trip(models.Model):
    """
    Represents a trip for a bus record and schedule.
    Fields:
        registration, record, schedule, route, booking_count
    Methods:
        total_filled_seats_percentage: Percentage of filled seats.
        total_available_seats_count: Number of available seats.
        get_total_available_seats_count: Returns available seats.
        get_total_filled_seats_percentage: Returns filled seat percentage.
        __str__: Returns schedule and route.
    """
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='trips')
    record = models.ForeignKey(BusRecord, on_delete=models.CASCADE, related_name='trips')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='trips')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='trips')
    booking_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('registration', 'record', 'schedule')
    
    @property
    def total_filled_seats_percentage(self):
        """
        Returns the percentage of filled seats for the trip.
        """
        if not self.record or not self.record.bus or self.record.bus.capacity == 0:
            return 0
        return round((self.booking_count * 100) / self.record.bus.capacity, 2)
    
    @property
    def total_available_seats_count(self):
        """
        Returns the number of available seats for the trip.
        """
        if not self.record or not self.record.bus or self.record.bus.capacity == 0:
            return 0
        return self.record.bus.capacity - self.booking_count
    
    def get_total_available_seats_count(self):
        """
        Returns the number of available seats for the trip.
        """
        return self.total_available_seats_count

    def get_total_filled_seats_percentage(self):
        """
        Returns the percentage of filled seats for the trip.
        """
        return self.total_filled_seats_percentage
    
    def __str__(self):
        """
        String representation of the Trip.
        """
        return f"{self.schedule} | {self.route}"


class Ticket(models.Model):
    """
    Represents a student's bus ticket.
    Fields:
        org, registration, institution, student_group, recipt, ticket_id, student_id, student_name, student_email, contact_no, alternative_contact_no, pickup_bus_record, drop_bus_record, pickup_point, drop_point, pickup_schedule, drop_schedule, ticket_type, status, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug and ticket_id if not present.
        __str__: Returns a string representation of the ticket.
    """
    TICKET_TYPES = ( 
        ("one_way", "One way"), 
        ("two_way", "Two way"),  
    )
    
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='tickets')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='tickets')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='tickets')
    student_group = models.ForeignKey('services.StudentGroup', on_delete=models.CASCADE, related_name='tickets')
    recipt = models.OneToOneField('services.Receipt', on_delete=models.CASCADE, related_name='ticket')
    ticket_id = models.CharField(max_length=300, unique=True)
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
    )
    alternative_contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
    )
    pickup_bus_record = models.ForeignKey(BusRecord, on_delete=models.CASCADE, null=True, default=None, blank=True, related_name='pickup_tickets')
    drop_bus_record = models.ForeignKey(BusRecord, on_delete=models.CASCADE, null=True, default=None, blank=True, related_name='drop_tickets')
    pickup_point = models.ForeignKey(Stop, on_delete=models.SET_NULL, null=True, default=None, blank=True, related_name='ticket_pickups')
    drop_point = models.ForeignKey(Stop, on_delete=models.SET_NULL, null=True, default=None, blank=True, related_name='ticket_drops')
    pickup_schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, default=None, related_name='pickup_tickets')
    drop_schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, default=None, related_name='drop_tickets')
    ticket_type = models.CharField(max_length=300, choices=TICKET_TYPES, default='twoway')
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the Ticket instance, generating a unique slug and ticket_id if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.registration.name}-{self.ticket_id}")
            self.slug = generate_unique_slug(self, base_slug)
        if not self.ticket_id:
            self.ticket_id = generate_unique_code(self, no_of_char=12, unique_field='ticket_id')
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String representation of the Ticket.
        """
        return f"Ticket for {self.student_name}"

class StudentGroup(models.Model):
    """
    Represents a group or class of students within an institution.
    Fields:
        org, institution, name, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the group name.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='groups')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='groups')
    name = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the StudentGroup instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        String representation of the StudentGroup.
        """
        return f"{self.name}"

class Receipt(models.Model):
    """
    Represents a payment receipt for a student.
    Fields:
        org, institution, registration, receipt_id, student_id, student_group, is_expired, created_at, updated_at, slug
    Methods:
        save: Converts student_id to uppercase, generates a unique slug if not present.
        __str__: Returns the receipt ID.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='recipts')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='recipts')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='recipts')
    receipt_id = models.CharField(max_length=500)
    student_id = models.CharField(max_length=20)
    student_group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE)
    is_expired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    class Meta:
        unique_together = ('registration', 'receipt_id', 'student_id')

    def save(self, *args, **kwargs):
        """
        Save the Receipt instance, converting student_id to uppercase and generating a unique slug if not present.
        """
        if self.student_id:
            self.student_id = self.student_id.upper()
        if not self.slug:
            base_slug = slugify(f"{self.student_id}-{self.created_at}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        """
        String representation of the Receipt.
        """
        return f"{self.receipt_id}"
    
def rename_uploaded_file_receipt(instance, filename):
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/{instance.institution.slug}/receipt_files/{slugify(base_name)}-{uuid4()}{ext}"

class ReceiptFile(models.Model):
    """
    Represents a file upload for receipt data.
    Fields:
        org, institution, registration, file, added, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the file name.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='recipt_files')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='recipt_files')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='recipt_files')
    file = models.FileField(upload_to=rename_uploaded_file_receipt, validators=[validate_excel_file])
    added = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the ReceiptFile instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.institution.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        """
        String representation of the ReceiptFile.
        """
        return f"{self.name}"

class FAQ(models.Model):
    """
    Represents a frequently asked question for a registration.
    Fields:
        org, registration, question, answer, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the receipt ID (may be a bug, should likely return question).
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='faqs')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the FAQ instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"faq-{self.question}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        """
        String representation of the FAQ.
        """
        return f"{self.receipt_id}"

class BusRequestComment(models.Model):
    """
    Represents a comment on a bus request.
    Fields:
        bus_request, comment, created_at, created_by
    Methods:
        __str__: Returns a string representation of the comment.
    """
    bus_request = models.ForeignKey('BusRequest', on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        """
        String representation of the BusRequestComment.
        """
        return f"Comment by {self.created_by} on {self.created_at}"

class BusRequest(models.Model):
    """
    Represents a student bus request.
    Fields:
        org, institution, registration, receipt, student_group, student_name, pickup_address, drop_address, contact_no, contact_email, status, created_at, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the student name.
    """
    STATUS_CHOICES = ( 
        ("open", "Open"), 
        ("closed", "Closed"),  
    )
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='bus_requests')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='bus_requests')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='bus_requests')
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    student_group = models.ForeignKey(StudentGroup, null=True, on_delete=models.SET_NULL)
    student_name = models.CharField(max_length=300)
    pickup_address = models.CharField(max_length=500)
    drop_address = models.CharField(max_length=500)
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
    )
    contact_email = models.EmailField()
    status = models.CharField(choices=STATUS_CHOICES, max_length=20, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    
    def save(self, *args, **kwargs):
        """
        Save the BusRequest instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"faq-{self.registration}-{self.student_name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        """
        String representation of the BusRequest.
        """
        return self.student_name

class ExportedFile(models.Model):
    """
    Represents a file exported by a user.
    Fields:
        user, file, slug, created_at
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns a string representation of the exported file.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # User who requested the export
    file = models.FileField(upload_to=rename_exported_file)  # Use custom upload_to function
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        Save the ExportedFile instance, generating a unique slug if not present.
        """
        if not self.slug:
            self.slug = slugify(f"{self.user.username}-{uuid4()}")
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String representation of the ExportedFile.
        """
        return f"Exported File for {self.user.username} - {self.created_at}"

class BusFile(models.Model):
    """
    Represents a file upload for bus data.
    Fields:
        org, user, file, name, added, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the creation date.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to=rename_bus_uploaded_file, validators=[validate_excel_file])
    name = models.CharField(max_length=255)
    added = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the BusFile instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        """
        String representation of the BusFile.
        """
        return f"{self.created_at}"

class UserActivity(models.Model):
    """
    Logs user actions for auditing and tracking.
    Fields:
        user, org, action, description, timestamp
    Methods:
        __str__: Returns a string representation of the user activity.
    """
    user = models.ForeignKey('core.User', on_delete=models.CASCADE)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE)  # Update the reference to Organisation
    action = models.CharField(max_length=255)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        String representation of the UserActivity.
        """
        return f'{self.user.email} - {self.action} - {self.timestamp}'

def log_user_activity(user, action, description):
    """
    Creates an instance of UserActivity to log user actions.
    Args:
        user (User): The user performing the action.
        action (str): A short description of the action.
        description (str): A detailed description of the action.
    """
    UserActivity.objects.create(
        user=user,
        org=user.profile.org,
        action=action,
        description=description
    )


class Notification(models.Model):
    """
    Represents a user notification.
    Fields:
        user, action, description, status, type, file_processing_task, priority, timestamp
    Methods:
        __str__: Returns a string representation of the notification.
    """
    STATUS_CHOICES = (
        ("unread", "Unread"),
        ("read", "Read"),
    )
    TYPE_CHOICES = (
        ("info", "Info"),
        ("warning", "Warning"),
        ("danger", "Error"),
        ("success", "Success"),
    )
    user = models.ForeignKey('core.User', on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="unread")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="info")
    file_processing_task = models.BooleanField(default=False)
    priority = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        String representation of the Notification.
        """
        return f'{self.user.email} - {self.action} - {self.timestamp}'

@receiver(post_delete, sender=Ticket)
def update_trip_booking_count_on_ticket_delete(sender, instance, **kwargs):
    """
    Signal to update the booking count of trips associated with a ticket when the ticket is deleted.
    """
    if instance.pickup_bus_record:
        trip = instance.pickup_bus_record.trips.filter(schedule=instance.pickup_schedule).first()
        if trip:
            trip.booking_count = max(0, trip.booking_count - 1)
            trip.save()

    if instance.drop_bus_record:
        trip = instance.drop_bus_record.trips.filter(schedule=instance.drop_schedule).first()
        if trip:
            trip.booking_count = max(0, trip.booking_count - 1)
            trip.save()


class StudentPassFile(models.Model):
    """
    Represents a file upload for a generated student pass.
    Fields:
        user, file, slug, created_at
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns a string representation of the student pass file.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # User who requested the file
    file = models.FileField(upload_to=rename_student_pass_file)  # Use custom upload_to function
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        Save the StudentPassFile instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.user}-{self.created_at}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String representation of the StudentPassFile.
        """
        return f"Generated student pass by {self.user} - {self.created_at}"


class BusReservationRequest(models.Model):
    """
    Represents a bus reservation request from an institution admin.
    Institution admins request buses by specifying seating capacity needed.
    Central admins can then approve and assign buses to fulfill the request.
    
    Fields:
        org, institution, registration, reservation_no, date, booked_by, contact_number,
        from_location, to_location, departure_time, arrival_time, total_duration,
        requested_capacity, purpose, status, created_by, created_at, updated_at, slug, 
        notes, approved_by, approved_at, rejected_reason
    Methods:
        save: Generates a unique slug and reservation_no if not present.
        total_assigned_capacity: Returns total capacity of assigned buses.
        is_capacity_fulfilled: Checks if assigned capacity meets requested capacity.
        __str__: Returns a string representation of the reservation request.
    """
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )
    
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='bus_reservation_requests')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='bus_reservation_requests')
    reservation_no = models.CharField(max_length=50, unique=True, blank=True, help_text="Unique reservation number")
    date = models.DateField(help_text="Date of the reservation")
    booked_by = models.CharField(max_length=200, help_text="Name of the person booking")
    contact_number = models.CharField(
        max_length=50,
        validators=[RegexValidator(r'^\d{10,15}$', 'Enter a valid contact number (10-15 digits)')],
        help_text="Contact number of the person booking"
    )
    from_location = models.CharField(max_length=500, help_text="Departure location (e.g., SFS School)")
    to_location = models.CharField(max_length=500, help_text="Arrival location (e.g., Christ Academy)")
    departure_time = models.TimeField(help_text="Departure time")
    arrival_time = models.TimeField(help_text="Arrival time")
    total_duration = models.DurationField(help_text="Total duration of the trip")
    requested_capacity = models.PositiveIntegerField(help_text="Total number of seats required")
    purpose = models.CharField(max_length=500, blank=True, null=True, help_text="Purpose of the bus reservation")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_reservations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes or special requirements")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reservations')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        """
        Save the BusReservationRequest instance, generating a unique slug and reservation_no if not present.
        """
        if not self.slug:
            base_slug = slugify(f"reservation-{self.institution.label}-{self.date}")
            self.slug = generate_unique_slug(self, base_slug)
        if not self.reservation_no:
            self.reservation_no = generate_unique_code(self, no_of_char=8, unique_field='reservation_no')
        
        super().save(*args, **kwargs)
    
    @property
    def total_assigned_capacity(self):
        """
        Returns the total capacity of all assigned buses for this reservation.
        """
        return sum(assignment.bus_record.bus.capacity for assignment in self.bus_assignments.all() if assignment.bus_record and assignment.bus_record.bus)
    
    @property
    def is_capacity_fulfilled(self):
        """
        Checks if the total assigned capacity meets or exceeds the requested capacity.
        """
        return self.total_assigned_capacity >= self.requested_capacity
    
    def __str__(self):
        """
        String representation of the BusReservationRequest.
        """
        return f"#{self.reservation_no} - {self.institution.name} - {self.date} ({self.requested_capacity} seats)"


class BusReservationAssignment(models.Model):
    """
    Represents a bus assignment to a reservation request.
    Multiple buses can be assigned to a single reservation request if needed.
    
    Fields:
        reservation_request, bus, assigned_by, assigned_at, notes
    Methods:
        __str__: Returns a string representation of the bus assignment.
    """
    reservation_request = models.ForeignKey(BusReservationRequest, on_delete=models.CASCADE, related_name='bus_assignments')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='reservation_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('reservation_request', 'bus')
    
    def __str__(self):
        """
        String representation of the BusReservationAssignment.
        """
        return f"{self.bus_record.label} assigned to {self.reservation_request}"