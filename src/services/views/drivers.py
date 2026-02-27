"""
drivers.py - Views for driver-related functionality

This module contains view classes for driver users including trip record management,
refueling record management, and trip information.

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


class DriverTripRecordListView(LoginRequiredMixin, DriverOnlyAccessMixin, ListView):
    """
    View for drivers to see and manage daily trip records (pickup/drop).
    
    Shows:
    - All trip records for the driver's assigned bus trips
    - Form to add new records (only if driver has an active assignment)
    """
    template_name = 'drivers/trip_records_list.html'
    context_object_name = 'trip_records'
    paginate_by = 20
    
    def get_queryset(self):
        from services.models import TripRecord, BusRecord, Registration
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        if not active_registration:
            return TripRecord.objects.none()
        
        # Get driver's bus record in active registration
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=self.request.user
        ).select_related('bus').first()
        
        if not bus_record:
            return TripRecord.objects.none()
        
        # Get trip records for this driver's bus
        records = TripRecord.objects.filter(
            bus=bus_record.bus,
            org=self.request.user.profile.org
        ).select_related('bus', 'recorded_by').order_by('-record_date', '-actual_time')
        
        return records
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from services.models import BusRecord, Registration, TripRecord
        from services.forms.drivers import DriverTripRecordForm
        
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
        context['form'] = DriverTripRecordForm()
        context['has_assignment'] = bus_record is not None
        
        # Calculate mileage statistics if bus is assigned
        if bus_record:
            mileage_data = TripRecord.calculate_mileage(bus_record.bus)
            context['mileage_data'] = mileage_data
        
        return context


class DriverTripRecordCreateView(LoginRequiredMixin, DriverOnlyAccessMixin, CreateView):
    """
    View for drivers to add daily trip records for their assigned bus.
    
    Only allows drivers to add records for their trips in the active registration.
    """
    template_name = 'drivers/trip_records_list.html'
    success_url = reverse_lazy('drivers:trip_records_list')
    
    def get_form_class(self):
        from services.forms.drivers import DriverTripRecordForm
        return DriverTripRecordForm
    
    def get_form_kwargs(self):
        """Pass the bus to the form for duplicate validation."""
        kwargs = super().get_form_kwargs()
        
        from services.models import BusRecord, Registration
        
        # Get active registration and driver's bus
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        if active_registration:
            bus_record = BusRecord.objects.filter(
                registration=active_registration,
                assigned_driver=self.request.user
            ).select_related('bus').first()
            
            if bus_record and bus_record.bus:
                kwargs['bus'] = bus_record.bus
        
        return kwargs
    
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
            return redirect('drivers:trip_records_list')
        
        # Get driver's bus record
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=request.user
        ).first()
        
        if not bus_record:
            messages.error(request, "You don't have an active bus assignment.")
            return redirect('drivers:trip_records_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        from services.models import BusRecord, Registration, log_user_activity
        from django.utils import timezone
        
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
        
        # Auto-populate fields
        now = timezone.localtime(timezone.now())
        form.instance.org = self.request.user.profile.org
        form.instance.bus = bus_record.bus
        form.instance.recorded_by = self.request.user
        form.instance.record_date = now.date()
        form.instance.actual_time = now.time()
        
        # Save the form
        response = super().form_valid(form)
        
        # Log activity
        log_user_activity(
            user=self.request.user,
            action='create',
            description=f"Added {form.instance.get_trip_type_display()} trip record for {bus_record.bus.registration_no} on {form.instance.record_date}"
        )
        
        messages.success(self.request, "Trip record added successfully!")
        
        # If HTMX request, return a response that triggers page reload
        if self.request.headers.get('HX-Request'):
            from django.http import HttpResponse
            response = HttpResponse()
            response['HX-Refresh'] = 'true'
            return response
        
        return response
    
    def form_invalid(self, form):
        """Handle form errors, especially for HTMX requests."""
        # If HTMX request, return only the error messages
        if self.request.headers.get('HX-Request'):
            from django.template.loader import render_to_string
            
            # Render error messages
            error_html = ""
            
            # Field-specific errors
            for field, errors in form.errors.items():
                if field == '__all__' or field == 'trip_type':
                    for error in errors:
                        error_html += f'<div class="alert alert-danger alert-dismissible fade show" role="alert">'
                        error_html += f'<i class="fa-solid fa-exclamation-triangle me-2"></i>{error}'
                        error_html += f'<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>'
                        error_html += f'</div>'
            
            from django.http import HttpResponse
            return HttpResponse(error_html)
        
        # For regular requests, use default behavior
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class DriverTripRecordUpdateView(LoginRequiredMixin, DriverOnlyAccessMixin, UpdateView):
    """
    View for drivers to update their trip records.
    
    Only allows drivers to update records for their own bus trips.
    """
    template_name = 'drivers/trip_record_update.html'
    success_url = reverse_lazy('drivers:trip_records_list')
    
    def get_form_class(self):
        from services.forms.drivers import DriverTripRecordForm
        return DriverTripRecordForm
    
    def get_queryset(self):
        from services.models import TripRecord, BusRecord, Registration
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        if not active_registration:
            return TripRecord.objects.none()
        
        # Get driver's bus record
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=self.request.user
        ).first()
        
        if not bus_record:
            return TripRecord.objects.none()
        
        # Return trip records for this driver's bus
        return TripRecord.objects.filter(
            bus=bus_record.bus,
            org=self.request.user.profile.org
        ).select_related('bus', 'recorded_by')
    
    def get_form_kwargs(self):
        """Pass the bus to the form for validation."""
        kwargs = super().get_form_kwargs()
        
        from services.models import BusRecord, Registration
        
        # Get active registration
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        # Get driver's assigned bus record
        if active_registration:
            bus_record = BusRecord.objects.filter(
                registration=active_registration,
                assigned_driver=self.request.user
            ).select_related('bus').first()
            
            if bus_record:
                kwargs['bus'] = bus_record.bus
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from services.models import BusRecord, Registration
        
        # Get active registration and bus record
        active_registration = Registration.objects.filter(
            org=self.request.user.profile.org,
            is_active=True
        ).first()
        
        bus_record = BusRecord.objects.filter(
            registration=active_registration,
            assigned_driver=self.request.user
        ).select_related('bus').first()
        
        context['bus_record'] = bus_record
        context['active_registration'] = active_registration
        
        return context
    
    def form_valid(self, form):
        from services.models import log_user_activity
        
        # Log activity
        log_user_activity(
            user=self.request.user,
            action='update',
            description=f"Updated {form.instance.get_trip_type_display()} trip record for {form.instance.bus} on {form.instance.record_date}"
        )
        
        messages.success(self.request, "Trip record updated successfully!")
        return super().form_valid(form)


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
        from django.utils import timezone
        
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
        refueling_record.refuel_date = timezone.localtime(timezone.now()).date()
        refueling_record.save()
        
        log_user_activity(
            self.request.user,
            f"Driver added refueling record for {bus_record.bus.registration_no}",
            f"Refueling record added: {refueling_record.fuel_amount}L on {refueling_record.refuel_date}"
        )
        
        messages.success(self.request, "Refueling record added successfully!")
        
        # If HTMX request, return a response that triggers page reload
        if self.request.headers.get('HX-Request'):
            from django.http import HttpResponse
            response = HttpResponse()
            response['HX-Refresh'] = 'true'
            return response
        
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        """Handle form errors, especially for HTMX requests."""
        # If HTMX request, return only the error messages
        if self.request.headers.get('HX-Request'):
            from django.http import HttpResponse
            
            # Render error messages
            error_html = ""
            
            # Field-specific errors
            for field, errors in form.errors.items():
                for error in errors:
                    error_html += f'<div class="alert alert-danger alert-dismissible fade show" role="alert">'
                    error_html += f'<i class="fa-solid fa-exclamation-triangle me-2"></i><strong>{field.replace("_", " ").title()}:</strong> {error}'
                    error_html += f'<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>'
                    error_html += f'</div>'
            
            return HttpResponse(error_html)
        
        # For regular requests, use default behavior
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
