"""
Bus reservation models for the services app.

This module defines models for managing bus reservations, assignments, and trip expenses.

Models:
    BusReservationRequest: Represents a bus reservation request from an institution admin.
    BusReservationAssignment: Represents a bus assignment to a reservation request.
    TripExpense: Represents expenses incurred for a bus assignment trip.
"""

from django.db import models
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.conf import settings
from config.utils import generate_unique_slug, generate_unique_code
from .core import Organisation, Institution
from .buses import Bus


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
        return sum(assignment.bus.capacity for assignment in self.bus_assignments.all() if assignment.bus)
    
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
    Each bus assignment must have an assigned driver (User with is_driver=True).
    
    Fields:
        reservation_request, bus, driver (required), assigned_by, assigned_at, notes
    Methods:
        __str__: Returns a string representation of the bus assignment.
    """
    reservation_request = models.ForeignKey(BusReservationRequest, on_delete=models.CASCADE, related_name='bus_assignments')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='reservation_assignments')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='driver_assignments', limit_choices_to={'profile__role': 'driver'}, help_text="Driver assigned to this bus")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bus_assignment_actions')
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('reservation_request', 'bus')
    
    def __str__(self):
        """
        String representation of the BusReservationAssignment.
        """
        return f"{self.bus.registration_no} assigned to {self.reservation_request}"


class TripExpense(models.Model):
    """
    Represents expenses incurred for a bus assignment trip.
    Tracks fuel costs, toll charges, maintenance expenses, driver bonus, and other costs.
    
    Fields:
        bus_assignment: Link to the BusReservationAssignment
        fuel_cost: Cost of fuel for the trip
        toll_charges: Toll/tax charges during the trip
        maintenance_cost: Any maintenance expenses during the trip
        driver_bonus: Bonus amount to be paid to the driver
        other_expenses: Any other miscellaneous expenses
        total_expense: Auto-calculated total of all expenses
        notes: Optional notes about the expenses
        recorded_by: User who recorded the expenses
        recorded_at: Timestamp when expenses were recorded
        updated_at: Timestamp when expenses were last updated
    
    Methods:
        save: Override to auto-calculate total_expense
        __str__: Returns a string representation of the trip expense
    """
    bus_assignment = models.OneToOneField(
        BusReservationAssignment, 
        on_delete=models.CASCADE, 
        related_name='trip_expense'
    )
    fuel_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Fuel cost for the trip"
    )
    toll_charges = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Toll and tax charges"
    )
    maintenance_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Maintenance expenses during the trip"
    )
    driver_bonus = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Bonus amount to be paid to the driver"
    )
    other_expenses = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Other miscellaneous expenses"
    )
    total_expense = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        editable=False,
        help_text="Total expense (auto-calculated)"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        help_text="Additional notes about the expenses"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='trip_expenses_recorded'
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-recorded_at']
        verbose_name = 'Trip Expense'
        verbose_name_plural = 'Trip Expenses'
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-calculate total_expense.
        """
        self.total_expense = (
            self.fuel_cost + 
            self.toll_charges + 
            self.maintenance_cost + 
            self.driver_bonus + 
            self.other_expenses
        )
        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        String representation of the TripExpense.
        """
        return f"Expenses for {self.bus_assignment.bus.registration_no} - {self.bus_assignment.reservation_request}"
