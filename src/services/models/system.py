"""
System models for the services app.

This module defines models for system-related functionality including
file exports, user activity logging, notifications, and student passes.

Models:
    ExportedFile: Files exported by users.
    UserActivity: Logs user actions.
    Notification: User notifications.
    StudentPassFile: File uploads for student passes.
"""

from uuid import uuid4
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from config.utils import generate_unique_slug
from .core import Organisation
from .utils import rename_exported_file, rename_student_pass_file


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
