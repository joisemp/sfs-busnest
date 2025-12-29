"""
models.py - Custom user and profile models for the core app

This module defines the custom User model (using email as the unique identifier) and the UserProfile model,
which extends user information and links users to organizations. It also includes a signal receiver to ensure
that deleting a UserProfile deletes the associated User object.

Classes:
- User: Custom user model with email as the unique identifier.
- UserProfile: Profile model linked to User and Organisation, with role flags and a unique slug.

Signals:
- delete_user_on_profile_delete: Deletes the User when the associated UserProfile is deleted.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from . user_manager import UserManager
from services.models import Organisation
from django.utils.text import slugify
from config.utils import generate_unique_slug
from django.db.models.signals import post_delete
from django.dispatch import receiver
    
    
class User(AbstractUser):
    """
    Custom User model that uses email as the unique identifier instead of username.
    Attributes:
        email (EmailField): The user's email address, used as the unique identifier.
        USERNAME_FIELD (str): The field used for authentication, set to 'email'.
        REQUIRED_FIELDS (list): List of required fields for createsuperuser, left empty.
        objects (UserManager): The manager for the User model.
    Notes:
        - Inherits from AbstractUser but removes the username field.
        - Ensures that each user has a unique email address.
    """
    username = None
    email = models.EmailField(_('email address'), unique = True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    
class UserProfile(models.Model):
    """
    Represents a user profile associated with a Django User and an Organisation.
    
    Fields:
        user (OneToOneField): Links to the Django User model. Acts as the primary key.
        org (ForeignKey): References the Organisation the user belongs to. Nullable.
        first_name (CharField): The user's first name.
        last_name (CharField): The user's last name.
        role (CharField): The single role assigned to this user (central_admin, institution_admin, driver, student).
        slug (SlugField): Unique slug for the profile, auto-generated if not provided.
    
    Role Constants:
        CENTRAL_ADMIN, INSTITUTION_ADMIN, DRIVER, STUDENT: Pre-defined role identifiers.
    
    Methods:
        save(*args, **kwargs): Auto-generates unique slug if not set.
        has_role(role): Check if user has a specific role.
        set_role(role): Set the user's role.
        get_role_display_name(): Get human-readable role name.
    
    Properties:
        is_central_admin, is_institution_admin, is_driver, is_student: Backward-compatible role checks.
    """
    
    # Role constants
    CENTRAL_ADMIN = 'central_admin'
    INSTITUTION_ADMIN = 'institution_admin'
    DRIVER = 'driver'
    STUDENT = 'student'
    
    ROLE_CHOICES = [
        (CENTRAL_ADMIN, _('Central Admin')),
        (INSTITUTION_ADMIN, _('Institution Admin')),
        (DRIVER, _('Driver')),
        (STUDENT, _('Student')),
    ]
    
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE, related_name='profile')
    org = models.ForeignKey(Organisation, null=True, on_delete=models.SET_NULL, related_name='org')
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default=STUDENT,
        help_text=_("Role assigned to this user")
    )
    slug = models.SlugField(unique=True, db_index=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.first_name}-{self.last_name}{self.org}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{str(self.first_name)} {str(self.last_name)}"
    
    # Role validation methods
    def has_role(self, role):
        """Check if user has a specific role."""
        return self.role == role
    
    def set_role(self, role):
        """Set the user's role."""
        if role in dict(self.ROLE_CHOICES):
            self.role = role
            self.save()
    
    def get_role_display_name(self):
        """Get human-readable role name."""
        return self.get_role_display()
    
    # Backward-compatible properties for existing code
    @property
    def is_central_admin(self):
        """Check if user has central admin role."""
        return self.role == self.CENTRAL_ADMIN
    
    @is_central_admin.setter
    def is_central_admin(self, value):
        """Set central admin role (for backward compatibility)."""
        if value:
            self.role = self.CENTRAL_ADMIN
    
    @property
    def is_institution_admin(self):
        """Check if user has institution admin role."""
        return self.role == self.INSTITUTION_ADMIN
    
    @is_institution_admin.setter
    def is_institution_admin(self, value):
        """Set institution admin role (for backward compatibility)."""
        if value:
            self.role = self.INSTITUTION_ADMIN
    
    @property
    def is_driver(self):
        """Check if user has driver role."""
        return self.role == self.DRIVER
    
    @is_driver.setter
    def is_driver(self, value):
        """Set driver role (for backward compatibility)."""
        if value:
            self.role = self.DRIVER
    
    @property
    def is_student(self):
        """Check if user has student role."""
        return self.role == self.STUDENT
    
    @is_student.setter
    def is_student(self, value):
        """Set student role (for backward compatibility)."""
        if value:
            self.role = self.STUDENT
    

@receiver(post_delete, sender=UserProfile)
def delete_user_on_profile_delete(sender, instance, **kwargs):
    """
    Signal receiver that deletes the associated User object when a UserProfile instance is deleted.

    Args:
        sender (Model): The model class (UserProfile) that sent the signal.
        instance (UserProfile): The actual instance of UserProfile being deleted.
        **kwargs: Additional keyword arguments.

    Behavior:
        - Attempts to delete the related User object when a UserProfile is deleted.
        - Prints a success message if the user is deleted successfully.
        - Prints an error message if an exception occurs during deletion.
    """
    try:
        user = instance.user
        user.delete()
        print(f"User {user.email} and associated profile deleted successfully.")
    except Exception as e:
        print(f"Error occurred while deleting user: {str(e)}")    