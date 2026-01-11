"""
Route-related models for the services app.

This module defines models for managing bus routes, stops, and route file uploads.

Models:
    Route: Represents a bus route.
    Stop: Represents a stop on a route.
    RouteFile: File uploads for route data.
"""

from django.db import models
from django.utils.text import slugify
from config.utils import generate_unique_slug
from config.validators import validate_excel_file
from .core import Organisation
from .utils import rename_uploaded_file


class Route(models.Model):
    """
    Represents a bus route for an organization and registration.
    Fields:
        org, registration, name, schedules, total_km, created_at, updated_at, slug
    Methods:
        save: Generates a unique slug if not present.
        __str__: Returns the route name.
    """
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='routes')
    registration = models.ForeignKey('services.Registration', on_delete=models.CASCADE, related_name='routes')
    name = models.CharField(max_length=200)
    schedules = models.ManyToManyField('services.Schedule', related_name='routes', blank=True)
    total_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='Total distance of the route in kilometers')
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
