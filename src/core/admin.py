from django.contrib import admin
from core.models import User, UserProfile
from django.utils.translation import gettext_lazy as _


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Custom Django admin configuration for the User model.
    This class customizes the admin interface for the User model by:
    - Displaying 'email', 'is_active', 'is_superuser', and 'is_staff' columns in the user list view.
    - Enabling search functionality on the 'email' field.
    - Organizing the user detail form into three sections:
        1. 'User': Contains the 'email' field.
        2. 'Permissions': Contains 'is_active', 'is_staff', 'is_superuser', and 'groups' fields.
        3. 'Important dates': Contains 'last_login' and 'date_joined' fields.
    """
    list_display = ('email', 'is_active', 'is_superuser', 'is_staff')
    search_fields = ('email',)
    
    fieldsets = (
        (_('User'), {'fields': ('email',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name')