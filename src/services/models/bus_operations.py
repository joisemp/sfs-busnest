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


class TripRecord(models.Model):
    """
    Represents a daily pickup/drop record entered by drivers.
    Simplified model - drivers record only 2 entries per day:
    - PICKUP: Entered when driver takes the bus and starts work (records starting odometer)
    - DROP: Entered when driver completes work and parks the bus (records ending odometer)
    
    Distance is calculated as: Drop odometer - Pickup odometer (same date)
    
    Fields:
        org: Organization reference
        bus: The bus for this record (auto-populated from driver's assignment)
        recorded_by: The user (driver) who created this record (auto-populated)
        record_date: Date when trip occurred
        trip_type: Type of trip - 'pickup' (start of work) or 'drop' (end of work)
        actual_time: Time when driver took the bus (pickup) or parked it (drop)
        odometer_reading: Odometer reading when starting work (pickup) or ending work (drop) - in km
        notes: Additional notes/observations by driver
        slug: Unique identifier for URL routing
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
        
    Methods:
        save: Auto-generates unique slug on creation
        distance_covered: Calculates distance for DROP records (drop odometer - pickup odometer)
        __str__: Returns formatted string with bus, type and date
    """
    TRIP_TYPE_CHOICES = [
        ('pickup', 'Pickup'),
        ('drop', 'Drop'),
    ]
    
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='trip_records')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='trip_records', help_text='Bus for this trip record')
    recorded_by = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='trip_records', help_text='Driver who recorded this entry')
    record_date = models.DateField(help_text='Date of the trip')
    trip_type = models.CharField(max_length=10, choices=TRIP_TYPE_CHOICES, default='pickup', help_text='Pickup (when starting work) or Drop (when completing work)')
    actual_time = models.TimeField(default='00:00:00', help_text='Time when driver started work (pickup) or completed work (drop)')
    odometer_reading = models.PositiveIntegerField(default=0, help_text='Odometer reading when taking the bus (pickup) or parking it (drop) - in km')
    notes = models.TextField(blank=True, help_text='Additional notes or observations')
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-record_date', '-actual_time']
        unique_together = [('bus', 'record_date', 'trip_type')]  # Only one pickup and one drop per bus per day
    
    def save(self, *args, **kwargs):
        """
        Overrides save to generate a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"{self.bus.registration_no}-{self.trip_type}-{self.record_date}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def distance_covered(self):
        """
        Calculate distance covered based on trip type:
        - For DROP records: Returns distance between pickup and drop of the same day
        - For PICKUP records: Returns None (trip not yet complete)
        
        Returns: Distance in km (int) or None if calculation not possible
        """
        if not self.odometer_reading:
            return None
        
        if self.trip_type == 'drop':
            # Find the pickup record for the same date
            pickup_record = TripRecord.objects.filter(
                bus=self.bus,
                record_date=self.record_date,
                trip_type='pickup',
                odometer_reading__isnull=False
            ).first()
            
            if pickup_record and self.odometer_reading > pickup_record.odometer_reading:
                return self.odometer_reading - pickup_record.odometer_reading
        
        return None
    
    @classmethod
    def calculate_mileage(cls, bus, start_date=None, end_date=None):
        """
        Calculate average mileage for a bus based on refueling records.
        
        For each refueling interval:
        - Distance = current odometer - previous odometer
        - Mileage = distance / previous fuel amount
        Average all interval mileages.
        
        Args:
            bus: Bus instance
            start_date: Start date for calculation (optional)
            end_date: End date for calculation (optional)
        
        Returns:
            dict: {
                'average_mileage': float (km per liter),
                'total_distance': int (km),
                'total_fuel': float (liters),
                'period': str
            }
        """
        from services.models import RefuelingRecord
        from datetime import date
        
        # Get refueling records for the period
        refuel_query = RefuelingRecord.objects.filter(bus=bus)
        if start_date:
            refuel_query = refuel_query.filter(refuel_date__gte=start_date)
        if end_date:
            refuel_query = refuel_query.filter(refuel_date__lte=end_date)
        
        refuel_records = list(refuel_query.order_by('refuel_date', 'odometer_reading'))
        
        if len(refuel_records) < 2:
            return {
                'average_mileage': 0,
                'total_distance': 0,
                'total_fuel': 0,
                'period': 'Insufficient data (need at least 2 refueling records)'
            }
        
        # Calculate mileage for each interval
        mileage_calculations = []
        total_distance = 0
        total_fuel = 0
        
        for i in range(1, len(refuel_records)):
            previous = refuel_records[i-1]
            current = refuel_records[i]
            
            distance = current.odometer_reading - previous.odometer_reading
            fuel_used = previous.fuel_amount  # Fuel from previous refueling
            
            if fuel_used > 0 and distance > 0:
                interval_mileage = distance / float(fuel_used)
                mileage_calculations.append(interval_mileage)
                total_distance += distance
                total_fuel += fuel_used
        
        average_mileage = sum(mileage_calculations) / len(mileage_calculations) if mileage_calculations else 0
        
        first_refuel = refuel_records[0]
        last_refuel = refuel_records[-1]
        
        return {
            'average_mileage': round(average_mileage, 2),
            'total_distance': total_distance,
            'total_fuel': float(total_fuel),
            'period': f"{first_refuel.refuel_date} to {last_refuel.refuel_date}"
        }
    
    def __str__(self):
        """
        String representation of the TripRecord.
        """
        return f"{self.bus.registration_no} - {self.get_trip_type_display()} - {self.record_date}"
