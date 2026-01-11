"""
Request models for the services app.

This module defines models for managing FAQs and bus requests.

Models:
    FAQ: Frequently asked questions for a registration.
    BusRequest: Student bus requests.
    BusRequestComment: Comments on bus requests.
"""

from django.db import models
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.conf import settings
from config.utils import generate_unique_slug
from .core import Organisation, Institution
from .registrations import Registration
from .tickets import StudentGroup, Receipt


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
