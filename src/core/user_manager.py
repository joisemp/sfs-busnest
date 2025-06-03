"""
user_manager.py - Custom user manager for the core app

This module defines a custom UserManager for the User model, using email as the unique identifier
instead of username. It provides methods for creating regular users and superusers, ensuring proper
field validation and normalization.

Classes:
- UserManager: Custom manager for user creation and management.
"""

from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    UserManager is a custom manager for the User model that uses email as the unique identifier instead of a username.
    Methods:
        _create_user(email, password, **extra_fields):
            Internal method to create and save a User with the given email and password.
            Raises a ValueError if the email is not provided.
            Normalizes the email, sets the password, and saves the user instance.
        create_user(email, password=None, **extra_fields):
            Creates and saves a regular user with the given email and password.
            Ensures 'is_staff' and 'is_superuser' are set to False by default.
        create_superuser(email, password, **extra_fields):
            Creates and saves a superuser with the given email and password.
            Ensures 'is_staff' and 'is_superuser' are set to True.
            Raises a ValueError if these fields are not set to True.
    """
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)