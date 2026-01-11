"""
Bus operations models for the services app.

This module defines models for managing bus records and trips.

Models:
    BusRecord: Represents a bus assigned to a registration.
    Trip: Represents a trip for a bus record and schedule.
"""

from django.db import models
from django.utils.text import slugify
from django.forms import ValidationError
from django.conf import settings
from config.utils import generate_unique_slug
from .core import Organisation
from .registrations import Registration, Schedule
from .buses import Bus
from .routes import Route


class BusRecord(models.Model):
    """
    Represents a bus assigned to a registration.
    Fields:
        org, bus, registration, label, assigned_driver, min_required_capacity, slug
    Methods:
        clean: Validates minimum required capacity.
        save: Generates a unique slug, updates label and min_required_capacity.
        __str__: Returns the label.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='bus_records')
    bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, blank=True, related_name='records')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='bus_records')
    label = models.CharField(max_length=20)
    assigned_driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bus_records', help_text='Driver assigned to this bus record')
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
            super().save(update_fields=['min_required_capacity'])  # Update only min_required_capacity

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
