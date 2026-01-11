"""
Bus-related models for the services app.

This module defines models for managing buses, refueling records, and bus file uploads.

Models:
    Bus: Represents a bus.
    RefuelingRecord: Represents a refueling record for a bus.
    BusFile: File uploads for bus data.
"""

from django.db import models
from django.utils.text import slugify
from django.conf import settings
from config.utils import generate_unique_slug
from config.validators import validate_excel_file
from .core import Organisation
from .utils import rename_bus_uploaded_file


class Bus(models.Model):
    """
    Represents a bus belonging to an organization.
    Fields:
        org, registration_no, capacity, is_available, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the bus registration number and capacity.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='buses')
    registration_no = models.CharField(max_length=100)
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


class RefuelingRecord(models.Model):
    """
    Represents a refueling record for a bus.
    Fields:
        org, bus, refuel_date, fuel_amount, fuel_cost, odometer_reading, fuel_type, notes, slug, created_at, updated_at
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns refuel info.
    """
    FUEL_TYPE_CHOICES = [
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
    ]
    
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='refueling_records')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='refueling_records')
    refuel_date = models.DateField()
    fuel_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount in liters or kWh")
    fuel_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total cost")
    odometer_reading = models.PositiveIntegerField(help_text="Odometer reading in km")
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPE_CHOICES, default='diesel')
    notes = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-refuel_date', '-created_at']
        verbose_name = 'Refueling Record'
        verbose_name_plural = 'Refueling Records'

    def save(self, *args, **kwargs):
        """
        Save the RefuelingRecord instance, generating a unique slug if not present.
        """
        if not self.slug:
            base_slug = slugify(f"refuel-{self.bus.registration_no}-{self.refuel_date}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String representation of the RefuelingRecord.
        """
        return f"{self.bus.registration_no} - {self.refuel_date} ({self.fuel_amount}L)"


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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
