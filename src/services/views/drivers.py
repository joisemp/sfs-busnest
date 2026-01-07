"""
drivers.py - Views for driver dashboard and driver-related functionality

This module contains view classes for driver users including dashboard,
trip management, and route information.
"""

from django.views.generic import TemplateView
from config.mixins.access_mixin import DriverOnlyAccessMixin


class DriverDashboardView(DriverOnlyAccessMixin, TemplateView):
    """
    Driver dashboard view that displays key information for drivers.
    
    Shows:
    - Driver profile information
    - Assigned trips and routes
    - Schedule information
    - Quick access to common driver tasks
    
    If driver is not assigned to any bus record, shows an empty state.
    """
    template_name = 'drivers/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = user.profile
        
        # Import here to avoid circular imports
        from services.models import BusRecord
        
        # Check if driver is assigned to any bus record
        assigned_bus_records = BusRecord.objects.filter(assigned_driver=user)
        
        context['profile'] = profile
        context['full_name'] = f"{profile.first_name} {profile.last_name}"
        context['org_name'] = profile.org.name if profile.org else "N/A"
        context['has_assignment'] = assigned_bus_records.exists()
        context['bus_records'] = assigned_bus_records
        
        return context
