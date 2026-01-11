"""
Core models for the services app.

This module defines the foundational models for the SFS Institutions system,
including organizations and institutions.

Models:
    Organisation: Represents an organization (e.g., a school group or company).
    Institution: Represents an institution under an organization.
"""

from django.db import models
from django.utils.text import slugify
from django.core.validators import RegexValidator
from config.utils import generate_unique_slug


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
