"""
Registration and schedule models for the services app.

This module defines models for managing registration periods and bus schedules.

Models:
    Registration: Represents a registration event or period.
    Schedule: Represents a schedule (e.g., morning, evening).
    ScheduleGroup: Groups pickup and drop schedules.
"""

from django.db import models
from django.utils.text import slugify
from config.utils import generate_unique_slug, generate_unique_code
from .core import Organisation


class Registration(models.Model):
    """
    Represents a registration event or period for an organization.
    Fields:
        org, name, instructions, status, code, is_active, slug
    Methods:
        save: Generates a unique slug and code if not present. Ensures only one active registration.
        __str__: Returns the registration name.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='registrations')
    name = models.CharField(max_length=200)
    instructions = models.TextField()
    status = models.BooleanField(default=False)
    code = models.CharField(max_length=100, unique=True, null=True)
    is_active = models.BooleanField(default=False, help_text='Only one registration can be active at a time')
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        """
        Save the Registration instance, generating a unique slug and code if not present.
        Ensures only one registration can be active per organization at a time.
        """
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        if not self.code:
            self.code = generate_unique_code(self, unique_field='code')
        
        # If setting this registration as active, deactivate all others in the same org
        if self.is_active:
            Registration.objects.filter(org=self.org, is_active=True).exclude(pk=self.pk).update(is_active=False)
        
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
