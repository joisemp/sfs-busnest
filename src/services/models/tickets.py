"""
Ticket and payment models for the services app.

This module defines models for managing tickets, payments, student groups, and receipts.

Models:
    Ticket: Represents a student's bus ticket.
    InstallmentDate: Represents an installment due date.
    Payment: Represents a payment record for a ticket.
    StudentGroup: Represents a group/class of students.
    Receipt: Represents a payment receipt for a student.
    ReceiptFile: File uploads for receipt data.
"""

from django.db import models
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.conf import settings
from config.utils import generate_unique_slug, generate_unique_code
from config.validators import validate_excel_file
from .core import Organisation, Institution
from .registrations import Registration, Schedule
from .bus_operations import BusRecord
from .routes import Stop
from .utils import rename_uploaded_file_receipt


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


class Ticket(models.Model):
    """
    Represents a student's bus ticket.
    Fields:
        org, registration, institution, student_group, recipt, ticket_id, student_id, student_name, student_email, contact_no, alternative_contact_no, pickup_bus_record, drop_bus_record, pickup_point, drop_point, pickup_schedule, drop_schedule, ticket_type, status, is_terminated, terminated_at, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug and ticket_id if not present.
        terminate: Soft delete the ticket by marking it as terminated.
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
    is_terminated = models.BooleanField(default=False)
    terminated_at = models.DateTimeField(null=True, blank=True)
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
    
    def get_total_paid_amount(self):
        """
        Returns the total amount paid for this ticket across all payments.
        """
        return self.payments.aggregate(models.Sum('amount'))['amount__sum'] or 0
    
    def get_pending_installments(self):
        """
        Returns installment dates for this ticket's registration that have no payment recorded.
        """
        paid_installment_ids = self.payments.values_list('installment_date_id', flat=True)
        return self.registration.installment_dates.exclude(
            id__in=paid_installment_ids
        ).filter(due_date__lte=models.functions.Now())
    
    def has_payment_due(self):
        """
        Returns True if there are pending installments with due dates that have passed.
        """
        return self.get_pending_installments().exists()
    
    def terminate(self):
        """
        Soft delete the ticket by marking it as terminated and updating trip booking counts.
        """
        from django.utils import timezone
        
        if not self.is_terminated:
            self.is_terminated = True
            self.terminated_at = timezone.now()
            self.save()
            
            # Update trip booking counts
            if self.pickup_bus_record:
                trip = self.pickup_bus_record.trips.filter(schedule=self.pickup_schedule).first()
                if trip:
                    trip.booking_count = max(0, trip.booking_count - 1)
                    trip.save()

            if self.drop_bus_record:
                trip = self.drop_bus_record.trips.filter(schedule=self.drop_schedule).first()
                if trip:
                    trip.booking_count = max(0, trip.booking_count - 1)
                    trip.save()


class InstallmentDate(models.Model):
    """
    Represents an installment due date for a registration cycle.
    Fields:
        org, registration, title, due_date, description, slug, created_at, updated_at
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns installment description.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='installment_dates')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='installment_dates')
    title = models.CharField(max_length=100, default='Installment', help_text="Installment title (e.g., 'First Installment', 'Mid-term Payment')")
    due_date = models.DateField(help_text="Date by which payment should be made")
    description = models.CharField(max_length=255, blank=True, help_text="Optional description of installment")
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['due_date']
    
    def save(self, *args, **kwargs):
        """
        Save the InstallmentDate instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.registration.slug}-{self.title}-{self.due_date}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        String representation of the InstallmentDate.
        """
        return f"{self.title} - {self.registration.name} (Due: {self.due_date})"


class Payment(models.Model):
    """
    Represents a payment record for a ticket.
    Fields:
        org, registration, ticket, institution, installment_date, payment_id, amount, payment_date, payment_mode, transaction_reference, notes, recorded_by, slug, created_at, updated_at
    Methods:
        save: Generates unique payment_id and slug if not present.
        __str__: Returns payment details.
    """
    PAYMENT_MODES = (
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('online', 'Online Transfer'),
        ('upi', 'UPI'),
        ('card', 'Card'),
        ('other', 'Other'),
    )
    
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='payments')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='payments')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='payments')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='payments')
    installment_date = models.ForeignKey(
        InstallmentDate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='payments',
        help_text="Associated installment (if applicable)"
    )
    payment_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique payment identifier")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Payment amount")
    payment_date = models.DateField(help_text="Date when payment was received")
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='cash')
    transaction_reference = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Transaction ID, cheque number, or other reference"
    )
    notes = models.TextField(blank=True, help_text="Additional notes about the payment")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='payments_recorded'
    )
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
        unique_together = [['ticket', 'installment_date']]
        constraints = [
            models.UniqueConstraint(
                fields=['ticket', 'installment_date'],
                name='unique_ticket_installment_payment',
                violation_error_message='A payment already exists for this ticket and installment.'
            )
        ]
    
    def save(self, *args, **kwargs):
        """
        Save the Payment instance, generating unique payment_id and slug if not present.
        """
        if not self.payment_id:
            self.payment_id = generate_unique_code(self, no_of_char=16, unique_field='payment_id')
        if not self.slug:
            base_slug = slugify(f"{self.ticket.ticket_id}-payment-{self.payment_id}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        String representation of the Payment.
        """
        return f"Payment {self.payment_id} - {self.ticket.student_name} - ₹{self.amount}"


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
