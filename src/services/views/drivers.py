"""
drivers.py - Views for driver dashboard and driver-related functionality

This module contains view classes for driver users including dashboard,
trip management, route information, and refueling record management.

Driver Access Pattern:
- Only one registration is active at a time (Registration.is_active=True)
- Each driver is assigned to one bus record in the active registration
- All driver operations are scoped to their assigned bus in the active registration
"""

from django.views.generic import TemplateView, CreateView, UpdateView, ListView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from config.mixins.access_mixin import DriverOnlyAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin


class DriverDashboardView(DriverOnlyAccessMixin, TemplateView):
    """
    Driver dashboard view that displays key information for drivers.
    
    Shows:
    - Driver profile information
    - Assigned bus record from the active registration
    - Quick access to common driver tasks
    
    If no active registration or driver not assigned, shows an empty state.
    """
    template_name = 'drivers/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = user.profile
        
        from services.models import BusRecord, Registration
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=profile.org,
            is_active=True
        ).first()
        
        # Get driver's bus record in active registration
        bus_record = None
        if active_registration:
            bus_record = BusRecord.objects.filter(
                registration=active_registration,
                assigned_driver=user
            ).select_related('bus', 'registration').first()
        
        context['profile'] = profile
        context['full_name'] = f"{profile.first_name} {profile.last_name}"
        context['org_name'] = profile.org.name if profile.org else "N/A"
        context['active_registration'] = active_registration
        context['bus_record'] = bus_record
        context['has_assignment'] = bus_record is not None
        
        return context


class DriverRefuelingListView(LoginRequiredMixin, DriverOnlyAccessMixin, ListView):
    """
    View for drivers to see refueling records for their assigned bus.
    
    Shows:
    - All refueling records for the driver's assigned bus
    - Form to add new records (only if driver has an active assignment)
    """
    template_name = 'drivers/refueling_list.html'
    context_object_name = 'refueling_records'
    
    def get_queryset(self):
        from services.models import RefuelingRecord, BusRecord, Registration
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        if not active_registration:
            return RefuelingRecord.objects.none()
        
        # Get driver's bus record in active registration
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=self.request.user
        ).select_related('bus').first()
        
        if not bus_record or not bus_record.bus:
            return RefuelingRecord.objects.none()
        
        # Get refueling records for this bus
        records = RefuelingRecord.objects.filter(
            bus=bus_record.bus,
            org=self.request.user.profile.org
        ).select_related('bus').order_by('-refuel_date', '-created_at')
        
        return records
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from services.models import BusRecord, Registration
        from services.forms.drivers import DriverRefuelingRecordForm
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        bus_record = None
        if active_registration:
            bus_record = BusRecord.objects.filter(
                registration=active_registration,
                assigned_driver=self.request.user
            ).select_related('bus').first()
        
        context['active_registration'] = active_registration
        context['bus_record'] = bus_record
        context['assigned_bus'] = bus_record.bus if bus_record else None
        context['form'] = DriverRefuelingRecordForm()
        context['has_assignment'] = bus_record is not None and bus_record.bus is not None
        
        return context


class DriverRefuelingCreateView(LoginRequiredMixin, DriverOnlyAccessMixin, CreateView):
    """
    View for drivers to add refueling records for their assigned bus.
    
    Only allows drivers to add records for their bus in the active registration.
    """
    template_name = 'drivers/refueling_create.html'
    success_url = reverse_lazy('drivers:refueling_list')
    
    def get_form_class(self):
        from services.forms.drivers import DriverRefuelingRecordForm
        return DriverRefuelingRecordForm
    
    def dispatch(self, request, *args, **kwargs):
        """Verify driver has an active assignment before allowing access."""
        from services.models import BusRecord, Registration
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=request.user.profile.org,
            is_active=True
        ).first()
        
        if not active_registration:
            messages.error(request, "No active registration found.")
            return redirect('drivers:dashboard')
        
        # Get driver's bus record
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=request.user
        ).select_related('bus').first()
        
        if not bus_record or not bus_record.bus:
            messages.error(request, "You don't have an active bus assignment.")
            return redirect('drivers:dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from services.models import BusRecord, Registration
        
        # Get active registration and driver's bus
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=self.request.user
        ).select_related('bus').first()
        
        context['bus_record'] = bus_record
        context['bus'] = bus_record.bus
        
        return context
    
    def form_valid(self, form):
        from services.models import BusRecord, Registration, log_user_activity
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        # Get driver's bus record
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=self.request.user
        ).select_related('bus').first()
        
        if not bus_record or not bus_record.bus:
            messages.error(self.request, "You don't have an active bus assignment.")
            return redirect('drivers:dashboard')
        
        refueling_record = form.save(commit=False)
        refueling_record.bus = bus_record.bus
        refueling_record.org = self.request.user.profile.org
        refueling_record.save()
        
        log_user_activity(
            self.request.user,
            f"Driver added refueling record for {bus_record.bus.registration_no}",
            f"Refueling record added: {refueling_record.fuel_amount}L on {refueling_record.refuel_date}"
        )
        
        messages.success(self.request, "Refueling record added successfully!")
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        messages.error(self.request, "Error adding refueling record. Please check the form.")
        return super().form_invalid(form)


class DriverRefuelingUpdateView(LoginRequiredMixin, DriverOnlyAccessMixin, UpdateView):
    """
    View for drivers to update refueling records for their assigned bus.
    
    Only allows drivers to update records for their bus in the active registration.
    """
    template_name = 'drivers/refueling_update.html'
    success_url = reverse_lazy('drivers:refueling_list')
    slug_url_kwarg = 'slug'
    
    def get_form_class(self):
        from services.models import RefuelingRecord
        from services.forms.drivers import DriverRefuelingRecordForm
        return DriverRefuelingRecordForm
    
    def get_queryset(self):
        """Only allow drivers to edit records for their assigned bus."""
        from services.models import RefuelingRecord, BusRecord, Registration
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        if not active_registration:
            return RefuelingRecord.objects.none()
        
        # Get driver's bus record
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=self.request.user
        ).select_related('bus').first()
        
        if not bus_record or not bus_record.bus:
            return RefuelingRecord.objects.none()
        
        # Return only records for this driver's bus
        return RefuelingRecord.objects.filter(
            bus=bus_record.bus,
            org=self.request.user.profile.org
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from services.models import BusRecord, Registration
        
        # Get active registration and driver's bus
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        bus_record = None
        if active_registration:
            bus_record = BusRecord.objects.filter(
                registration=active_registration,
                assigned_driver=self.request.user
            ).select_related('bus').first()
        
        context['bus_record'] = bus_record
        context['bus'] = bus_record.bus if bus_record else None
        
        return context
    
    def form_valid(self, form):
        from services.models import log_user_activity
        
        refueling_record = form.save()
        
        log_user_activity(
            self.request.user,
            f"Driver updated refueling record for {refueling_record.bus.registration_no}",
            f"Refueling record updated: {refueling_record.fuel_amount}L on {refueling_record.refuel_date}"
        )
        
        messages.success(self.request, "Refueling record updated successfully!")
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        messages.error(self.request, "Error updating refueling record. Please check the form.")
        return super().form_invalid(form)


class DriverStudentsListView(LoginRequiredMixin, DriverOnlyAccessMixin, TemplateView):
    """
    View for drivers to see students assigned to their bus schedules.
    
    Shows all students grouped by schedule (morning/evening) for the driver's assigned bus.
    """
    template_name = 'drivers/students_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from services.models import BusRecord, Registration, Ticket, Schedule
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        bus_record = None
        schedules_data = []
        
        if active_registration:
            bus_record = BusRecord.objects.filter(
                registration=active_registration,
                assigned_driver=self.request.user
            ).select_related('bus').first()
            
            if bus_record:
                # Get all schedules for this registration
                schedules = Schedule.objects.filter(
                    registration=active_registration
                ).order_by('start_time')
                
                for schedule in schedules:
                    # Get pickup tickets for this schedule and bus record
                    pickup_tickets = Ticket.objects.filter(
                        registration=active_registration,
                        pickup_bus_record=bus_record,
                        pickup_schedule=schedule,
                        is_terminated=False,
                        status=True
                    ).select_related(
                        'student_group', 'institution', 'pickup_point'
                    ).order_by('student_name')
                    
                    # Get drop tickets for this schedule and bus record
                    drop_tickets = Ticket.objects.filter(
                        registration=active_registration,
                        drop_bus_record=bus_record,
                        drop_schedule=schedule,
                        is_terminated=False,
                        status=True
                    ).select_related(
                        'student_group', 'institution', 'drop_point'
                    ).order_by('student_name')
                    
                    if pickup_tickets.exists() or drop_tickets.exists():
                        schedules_data.append({
                            'schedule': schedule,
                            'pickup_students': pickup_tickets,
                            'drop_students': drop_tickets,
                            'total_students': pickup_tickets.count() + drop_tickets.count()
                        })
        
        context['active_registration'] = active_registration
        context['bus_record'] = bus_record
        context['assigned_bus'] = bus_record.bus if bus_record else None
        context['schedules_data'] = schedules_data
        context['has_assignment'] = bus_record is not None and bus_record.bus is not None
        
        return context
