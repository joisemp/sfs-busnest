"""
Utility functions for the services models module.

This module provides helper functions for file upload path generation and user activity logging.
These functions are used across various models in the services app.

Functions:
    rename_uploaded_file: Custom file path generator for route file uploads.
    rename_bus_uploaded_file: Custom file path generator for bus file uploads.
    rename_exported_file: Custom file path generator for exported files.
    rename_student_pass_file: Custom file path generator for student pass files.
    rename_uploaded_file_receipt: Custom file path generator for receipt file uploads.
    log_user_activity: Helper function to log user actions.
"""

import os
from uuid import uuid4
from django.utils.text import slugify


def rename_uploaded_file(instance, filename):
    """
    Generate custom upload path for route files.
    
    Args:
        instance: The RouteFile model instance
        filename: The original filename
        
    Returns:
        str: The custom upload path
    """
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/route_files/{slugify(base_name)}-{uuid4()}{ext}"


def rename_bus_uploaded_file(instance, filename):
    """
    Generate custom upload path for bus files.
    
    Args:
        instance: The BusFile model instance
        filename: The original filename
        
    Returns:
        str: The custom upload path
    """
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/bus_files/{slugify(base_name)}-{uuid4()}{ext}"


def rename_exported_file(instance, filename):
    """
    Generate custom upload path for exported files.
    
    Args:
        instance: The ExportedFile model instance
        filename: The original filename
        
    Returns:
        str: The custom upload path
    """
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.user.profile.org.slug}/exported_files/{slugify(base_name)}-{uuid4()}{ext}"


def rename_student_pass_file(instance, filename):
    """
    Generate custom upload path for student pass files.
    
    Args:
        instance: The StudentPassFile model instance
        filename: The original filename
        
    Returns:
        str: The custom upload path
    """
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.user.profile.org.slug}/student_pass/{slugify(base_name)}-{uuid4()}{ext}"


def rename_uploaded_file_receipt(instance, filename):
    """
    Generate custom upload path for receipt files.
    
    Args:
        instance: The ReceiptFile model instance
        filename: The original filename
        
    Returns:
        str: The custom upload path
    """
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/{instance.institution.slug}/receipt_files/{slugify(base_name)}-{uuid4()}{ext}"


def log_user_activity(user, action, description):
    """
    Creates an instance of UserActivity to log user actions.
    
    Args:
        user (User): The user performing the action.
        action (str): A short description of the action.
        description (str): A detailed description of the action.
    """
    # Import here to avoid circular import
    from .system import UserActivity
    
    UserActivity.objects.create(
        user=user,
        org=user.profile.org,
        action=action,
        description=description
    )
