"""
mechanics.py - Views for mechanic-related functionality

This module contains view classes for mechanic users including dashboard,
maintenance record management, and bus maintenance tracking.

Mechanic Access Pattern:
- Mechanics can manage and track bus maintenance and repair records
- Operations are scoped to their organization
- Can view and add maintenance records for all buses in the organization
"""

from django.views.generic import TemplateView, CreateView, UpdateView, ListView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from config.mixins.access_mixin import MechanicOnlyAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin


class MechanicDashboardView(LoginRequiredMixin, MechanicOnlyAccessMixin, TemplateView):
    """
    Main dashboard view for mechanics.
    
    Shows:
    - Overview of buses in the organization
    - Recent maintenance activities
    - Pending maintenance tasks
    """
    template_name = 'mechanics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from services.models import Bus, Registration, BusRecord
        
        # Get mechanic's organization
        org = self.request.user.profile.org
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=org,
            is_active=True
        ).first()
        
        # Get all buses in the organization
        all_buses = Bus.objects.filter(
            org=org
        ).select_related('org').order_by('registration_no')
        
        # Separate available and maintenance buses
        available_buses = all_buses.filter(is_available=True)
        maintenance_buses = all_buses.filter(is_available=False)
        
        # Get bus label mapping from active registration
        bus_labels = {}
        if active_registration:
            bus_records = BusRecord.objects.filter(
                registration=active_registration,
                org=org
            ).select_related('bus')
            bus_labels = {record.bus.id: record.label for record in bus_records}
        
        context['profile'] = self.request.user.profile
        context['active_registration'] = active_registration
        context['available_buses'] = available_buses
        context['maintenance_buses'] = maintenance_buses
        context['bus_labels'] = bus_labels
        context['total_buses'] = all_buses.count()
        context['total_available'] = available_buses.count()
        context['total_maintenance'] = maintenance_buses.count()
        context['has_buses'] = all_buses.exists()
        
        return context
