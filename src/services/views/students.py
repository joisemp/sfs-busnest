"""
Views for student-side bus registration and booking in the SFS Institutions system.

This module contains Django class-based and function-based views for student interactions, including:
- Student validation and registration
- Rules and regulations display
- Stop and schedule group selection
- Bus search and booking
- Bus request creation
- Success and error pages for booking and requests

Each view is responsible for a specific step in the student bus registration and booking workflow, handling session state, form validation, and context preparation for templates.
"""

from django.db import transaction
from django.http import HttpResponseRedirect
from django.views.generic import FormView, ListView, CreateView, TemplateView, View
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from services.forms.students import StopSelectForm, ValidateStudentForm, TicketForm, BusRequestForm
from services.models import Registration, ScheduleGroup, Ticket, Schedule, Receipt, BusRequest, BusRecord, Trip, Stop, Route
from config.mixins.access_mixin import RegistrationOpenCheckMixin
from services.tasks import send_email_task
from services.utils.utils import get_filtered_bus_records

class ValidateStudentFormView(RegistrationOpenCheckMixin, FormView):
    """
    View for validating a student's receipt and student ID for registration.
    Prevents duplicate ticket creation for the same receipt.
    """
    template_name = 'students/validate_student_form.html'
    form_class = ValidateStudentForm  
    
    def form_valid(self, form):
        """
        Validates the receipt and student ID, stores details in session, and checks for existing tickets.
        """
        try:
            receipt_id = form.cleaned_data['receipt_id']
            student_id = form.cleaned_data['student_id']
            
            registration = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
            
            # Validate receipt
            receipt = Receipt.objects.get(registration=registration, receipt_id=receipt_id, student_id=student_id)

            # Store details in the session
            self.request.session['receipt_id'] = receipt.pk
            self.request.session['student_id'] = receipt.student_id

            # Check if a ticket already exists for this receipt
            if Ticket.objects.filter(recipt_id=receipt.pk).exists():
                form.add_error(None, "A ticket already exists for this receipt.")
                return self.form_invalid(form)

            return super().form_valid(form)

        except Receipt.DoesNotExist:
            form.add_error(None, "Receipt or student with the following ID does not exist. Please try again.")
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """
        Adds registration to the context for the template.
        """
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    
    def get_success_url(self):
        """
        Returns the URL for the rules and regulations page after validation.
        """
        registration_code = self.kwargs.get('registration_code')
        return reverse('students:rules_and_regulations', kwargs={'registration_code': registration_code})
    

class RulesAndRegulationsView(RegistrationOpenCheckMixin, TemplateView):
    """
    View to display rules and regulations to the student.
    """
    template_name = 'students/rules_and_regulations.html'
    
    def get_context_data(self, **kwargs):
        """
        Adds registration to the context for the template.
        """
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context


class StopSelectFormView(RegistrationOpenCheckMixin, FormView):
    """
    View for students to select a stop for bus search.
    """
    template_name = 'students/search_form.html'
    form_class = StopSelectForm

    def get_registration(self):
        """
        Fetch registration using the code from the URL.
        """
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)
    
    def get_form(self, form_class=None):
        """
        Customizes the form's queryset for stops based on selected schedule group.
        Only shows stops that are available in routes for the selected schedule group's schedules.
        """
        form = super().get_form(form_class)
        registration = self.get_registration()
        
        # Get the selected schedule group from session
        schedule_group_id = self.request.session.get('schedule_group_id')
        
        if schedule_group_id:
            schedule_group = get_object_or_404(ScheduleGroup, id=schedule_group_id)
            
            # Get pickup and drop flags from session
            pickup = self.request.session.get('pickup')
            drop = self.request.session.get('drop')
            
            # Determine which schedules to filter by
            schedule_ids = []
            if schedule_group.allow_one_way:
                if pickup:
                    schedule_ids.append(int(pickup))
                if drop:
                    schedule_ids.append(int(drop))
            else:
                # Two-way booking - include both schedules
                schedule_ids = [schedule_group.pick_up_schedule.id, schedule_group.drop_schedule.id]
            
            # Only filter if we have schedule IDs to filter by
            if schedule_ids:
                if schedule_group.allow_one_way:
                    # One-way allowed: show routes with trips for ANY selected schedule
                    route_ids = Trip.objects.filter(
                        schedule_id__in=schedule_ids,
                        registration=registration,
                        route__schedules__id__in=schedule_ids  # Additional check: route must be associated with schedule
                    ).values_list('route_id', flat=True).distinct()
                else:
                    # Two-way mandatory: show ONLY routes with trips for BOTH schedules
                    pickup_schedule_id = schedule_group.pick_up_schedule.id
                    drop_schedule_id = schedule_group.drop_schedule.id
                    
                    # Get routes that have trips with pickup schedule
                    pickup_route_ids = set(Trip.objects.filter(
                        schedule_id=pickup_schedule_id,
                        registration=registration,
                        route__schedules__id=pickup_schedule_id
                    ).values_list('route_id', flat=True))
                    
                    # Get routes that have trips with drop schedule
                    drop_route_ids = set(Trip.objects.filter(
                        schedule_id=drop_schedule_id,
                        registration=registration,
                        route__schedules__id=drop_schedule_id
                    ).values_list('route_id', flat=True))
                    
                    # Only routes that have BOTH schedules
                    route_ids = list(pickup_route_ids.intersection(drop_route_ids))
                
                # Filter stops to only those in the relevant routes
                form.fields['stop'].queryset = Stop.objects.filter(
                    registration=registration,
                    route_id__in=route_ids
                ).order_by('name').distinct()
            else:
                # Fallback if no schedules selected
                form.fields['stop'].queryset = registration.stops.all().order_by('name')
        else:
            # Fallback: show all stops if no schedule group selected
            form.fields['stop'].queryset = registration.stops.all().order_by('name')
        
        return form
    
    def get_context_data(self, **kwargs):
        """
        Adds registration to the context for the template.
        """
        context = super().get_context_data(**kwargs)
        context['registration'] = self.get_registration()
        return context

    def form_valid(self, form):
        """
        Stores the selected stop in the session and proceeds to the next step.
        """
        stop = form.cleaned_data['stop']
        self.request.session['stop_id'] = stop.id
        return super().form_valid(form)

    def get_success_url(self):
        """
        Returns the URL for bus search results after stop selection.
        """
        registration_code = self.get_registration().code
        return reverse('students:bus_search_results', kwargs={'registration_code': registration_code})
    

class SelectScheduleGroupView(RegistrationOpenCheckMixin, View):
    """
    View for students to select a schedule group and pickup/drop options.
    """

    template_name = 'students/select_schedule_group.html'

    def get(self, request, registration_code):
        """
        Renders the schedule group selection page for the student.
        """
        registration = get_object_or_404(Registration, code=registration_code)
        schedule_groups = ScheduleGroup.objects.filter(registration=registration)
        return render(
            request,
            self.template_name,
            {
                'schedule_groups': schedule_groups,
                'error_message': '',  # Always include this
            }
        )

    def post(self, request, registration_code):
        """
        Handles the schedule group selection and stores pickup/drop choices in the session.
        """
        selected_id = request.POST.get("schedule_group")
        pickup = request.POST.get(f"pickup_{selected_id}")  # Checkbox value
        drop = request.POST.get(f"drop_{selected_id}")  # Checkbox value

        if not selected_id:
            registration = get_object_or_404(Registration, code=registration_code)
            
            schedule_groups = ScheduleGroup.objects.filter(registration=registration)
            return render(
                request,
                self.template_name,
                {
                    'schedule_groups': schedule_groups,
                    'error_message': "Please select a schedule group.",
                }
            )

        selected_group = ScheduleGroup.objects.get(id=selected_id)
        
        # Store schedule group ID in session
        self.request.session['schedule_group_id'] = selected_group.id
        
        # Store actual schedule IDs (not checkbox values) for filtering
        if pickup:
            self.request.session['pickup'] = selected_group.pick_up_schedule.id
        else:
            self.request.session['pickup'] = None
            
        if drop:
            self.request.session['drop'] = selected_group.drop_schedule.id
        else:
            self.request.session['drop'] = None

        if pickup and drop:
            return HttpResponseRedirect(reverse('students:pickup_stop_select', kwargs={'registration_code': registration_code}))
        return HttpResponseRedirect(reverse('students:stop_select', kwargs={'registration_code': registration_code}))


class BusSearchResultsView(RegistrationOpenCheckMixin, ListView):
    """
    View to display available buses for the selected stop and schedule group.
    """
    template_name = 'students/search_results.html'
    context_object_name = 'buses'

    def get_queryset(self):
        """
        Returns queryset of buses filtered by selected schedule(s) and stop.
        """
        # Retrieve the registration based on the registration code
        registration_code = self.kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)

        # Get pickup point, drop point, and schedule from session
        stop_id = self.request.session.get('stop_id')
        schedule_group_id = self.request.session.get('schedule_group_id')
        pickup = self.request.session.get('pickup')
        drop = self.request.session.get('drop')
        

        schedule_group = ScheduleGroup.objects.get(id=int(schedule_group_id))
        
        
        schedule_ids = [schedule_group.pick_up_schedule.id, schedule_group.drop_schedule.id]
        
        if schedule_group.allow_one_way:
            if pickup:
                schedule_ids = [int(pickup)]
            if drop:
                schedule_ids = [int(drop)]
            if pickup and drop:
                schedule_ids = [int(pickup), int(drop)]

        buses = get_filtered_bus_records(schedule_ids, int(stop_id))

        return buses
    
    def get(self, request, *args, **kwargs):
        """
        Redirects to 'bus_not_found' if no buses are found, otherwise renders results.
        """
        self.object_list = self.get_queryset()
        if not self.object_list:
            registration_code = self.kwargs.get('registration_code')
            return HttpResponseRedirect(reverse('students:bus_not_found', kwargs={'registration_code': registration_code}))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Include additional context like the registration."""
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context


class BusNotFoundView(RegistrationOpenCheckMixin, TemplateView):
    """
    View to display a message when no buses are found for the student's search.
    """
    template_name = 'students/bus_not_found.html'
    
    def get_context_data(self, **kwargs):
        """
        Adds registration to the context for the template.
        """
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    

class BusRequestFormView(RegistrationOpenCheckMixin, CreateView):
    """
    View for students to submit a bus request if no suitable bus is found.
    Prevents duplicate requests for the same receipt and registration.
    """
    model = BusRequest
    template_name = 'students/bus_request.html'
    form_class = BusRequestForm
    
    @transaction.atomic
    def form_valid(self, form):
        """
        Validates and saves the bus request, ensuring no duplicate exists.
        """
        registration = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        receipt = get_object_or_404(Receipt, id=self.request.session.get('receipt_id'))
        
        # Check if a request already exists for this receipt and registration
        if BusRequest.objects.filter(receipt=receipt, registration=registration).exists():
            form.add_error(None, "A bus request already exists for this receipt in the current registration.")
            return self.form_invalid(form)
        
        bus_request = form.save(commit=False)
        bus_request.org = registration.org
        bus_request.registration = registration
        bus_request.receipt = receipt
        bus_request.institution = receipt.institution
        bus_request.student_group = receipt.student_group
        bus_request.save()
        return HttpResponseRedirect(reverse('students:bus_request_success', kwargs={'registration_code': registration.code}))
    

class BusRequestSuccessView(RegistrationOpenCheckMixin, TemplateView):
    """
    View to display a success message after a bus request is submitted.
    """
    template_name = 'students/bus_request_success.html'
    
    def get_context_data(self, **kwargs):
        """
        Adds registration to the context for the template.
        """
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    

class BusBookingView(RegistrationOpenCheckMixin, CreateView):
    """
    View for students to book a bus ticket, handling both one-way and two-way bookings.
    Sends a confirmation email upon successful booking.
    """
    model = Ticket
    template_name = 'students/bus_booking.html'
    form_class = TicketForm
    
    def get_form(self, form_class=None):
        """
        Customizes the form fields and queryset for pickup/drop points based on booking type.
        """
        form = super().get_form(form_class)
        self.schedule_group_id = self.request.session.get('schedule_group_id')
        self.pickup_id = self.request.session.get('pickup')
        self.drop_id = self.request.session.get('drop')
        self.schedule_group = ScheduleGroup.objects.get(id=int(self.schedule_group_id))
        
        # Initialize attributes
        self.pickup_bus_record = None
        self.drop_bus_record = None
        
        if self.schedule_group.allow_one_way:
            if not self.pickup_id and self.drop_id:
                self.bus_record = get_object_or_404(BusRecord, slug=self.request.GET.get('bus_slug'))
            elif self.pickup_id and not self.drop_id:
                self.bus_record = get_object_or_404(BusRecord, slug=self.request.GET.get('bus_slug'))
            else:
                self.pickup_bus_record = get_object_or_404(BusRecord, slug=self.request.GET.get('pickup_bus'))
                self.drop_bus_record = get_object_or_404(BusRecord, slug=self.request.GET.get('drop_bus'))
        else:
            self.bus_record = get_object_or_404(BusRecord, slug=self.request.GET.get('bus_slug'))
        
        
        if self.schedule_group.allow_one_way:
            if self.pickup_id and not self.drop_id:
                pickup_trip = Trip.objects.get(record=self.bus_record, schedule=self.schedule_group.pick_up_schedule)
                form.fields['pickup_point'].queryset = pickup_trip.route.stops.all()
                del form.fields['drop_point']
            elif self.drop_id and not self.pickup_id:
                drop_trip = Trip.objects.get(record=self.bus_record, schedule=self.schedule_group.drop_schedule)
                form.fields['drop_point'].queryset = drop_trip.route.stops.all()
                del form.fields['pickup_point']
            else:
                pickup_trip = Trip.objects.get(record=self.pickup_bus_record, schedule=self.schedule_group.pick_up_schedule)
                drop_trip = Trip.objects.get(record=self.drop_bus_record, schedule=self.schedule_group.drop_schedule)
                form.fields['pickup_point'].queryset = pickup_trip.route.stops.all()
                form.fields['drop_point'].queryset = drop_trip.route.stops.all()
        else:
            pickup_trip = Trip.objects.get(record=self.bus_record, schedule=self.schedule_group.pick_up_schedule)
            drop_trip = Trip.objects.get(record=self.bus_record, schedule=self.schedule_group.drop_schedule)
            form.fields['pickup_point'].queryset = pickup_trip.route.stops.all()
            form.fields['drop_point'].queryset = drop_trip.route.stops.all()
        return form
    
    @transaction.atomic
    def form_valid(self, form):
        """
        Validates and saves the ticket, updates trip booking counts, and sends confirmation email.
        """
        ticket = form.save(commit=False)
        registration = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        receipt_id = self.request.session.get('receipt_id')
        std_id = self.request.session.get('student_id')
        receipt = get_object_or_404(Receipt, id=receipt_id)

        # Check if a ticket already exists for this receipt
        if Ticket.objects.filter(recipt=receipt).exists():
            form.add_error(None, "A ticket already exists for this receipt.")
            return self.form_invalid(form)

        ticket.org = registration.org
        ticket.registration = registration
        ticket.institution = receipt.institution
        ticket.student_group = receipt.student_group
        ticket.recipt = receipt
        ticket.student_id = std_id
        
        
        if self.schedule_group.allow_one_way:
            if self.pickup_id and not self.drop_id:
                pickup_bus_record = self.bus_record
                drop_bus_record = None
            elif not self.pickup_id and self.drop_id:
                pickup_bus_record = None
                drop_bus_record = self.bus_record
            else:
                pickup_bus_record = self.pickup_bus_record
                drop_bus_record = self.drop_bus_record
        else:
            pickup_bus_record = self.bus_record
            drop_bus_record = self.bus_record

        try:
            pickup_trip = Trip.objects.get(record=pickup_bus_record, schedule=self.schedule_group.pick_up_schedule)
        except Trip.DoesNotExist:
            pickup_trip = None
            
        try:
            drop_trip = Trip.objects.get(record=drop_bus_record, schedule=self.schedule_group.drop_schedule)
        except Trip.DoesNotExist:
            drop_trip = None
            
        if 'pickup_point' in form.fields:
                form.fields['pickup_point'].queryset = pickup_trip.route.stops.all()
        if 'drop_point' in form.fields:
                form.fields['drop_point'].queryset = drop_trip.route.stops.all()

        if self.schedule_group.allow_one_way:
            if self.pickup_id and not self.drop_id:  # One-way pickup only
                if not form.cleaned_data.get('pickup_point'):
                    form.add_error('pickup_point', "Pickup point must be selected.")
                    return self.form_invalid(form)
                ticket.pickup_bus_record = self.bus_record
                ticket.pickup_schedule = self.schedule_group.pick_up_schedule
                if pickup_trip:
                    pickup_trip.booking_count += 1
                ticket.ticket_type = 'one_way'

            elif self.drop_id and not self.pickup_id:  # One-way drop only
                if not form.cleaned_data.get('drop_point'):
                    form.add_error('drop_point', "Drop point must be selected.")
                    return self.form_invalid(form)
                ticket.drop_bus_record = self.bus_record
                ticket.drop_schedule = self.schedule_group.drop_schedule
                if drop_trip:
                    drop_trip.booking_count += 1
                ticket.ticket_type = 'one_way'

            else:  # Both pickup and drop (two-way)
                if not form.cleaned_data.get('pickup_point') or not form.cleaned_data.get('drop_point'):
                    form.add_error(None, "Both pickup and drop points must be selected.")
                    return self.form_invalid(form)

                ticket.pickup_bus_record = self.pickup_bus_record
                ticket.drop_bus_record = self.drop_bus_record
                ticket.pickup_schedule = self.schedule_group.pick_up_schedule
                ticket.drop_schedule = self.schedule_group.drop_schedule
                if pickup_trip:
                    pickup_trip.booking_count += 1
                if drop_trip:
                    drop_trip.booking_count += 1
                ticket.ticket_type = 'two_way'
        else:
            if not form.cleaned_data.get('pickup_point') or not form.cleaned_data.get('drop_point'):
                    form.add_error(None, "Both pickup and drop points must be selected.")
                    return self.form_invalid(form)
            
            ticket.pickup_bus_record = self.bus_record
            ticket.drop_bus_record = self.bus_record
            ticket.pickup_schedule = self.schedule_group.pick_up_schedule
            ticket.drop_schedule = self.schedule_group.drop_schedule
            if pickup_trip:
                pickup_trip.booking_count += 1
            if drop_trip:
                drop_trip.booking_count += 1
            ticket.ticket_type = 'two_way'

        ticket.status = True

        if pickup_trip:
            pickup_trip.save()
        if drop_trip:
            drop_trip.save()
        ticket.save()
        
        subject = "Booking Confirmation"
        message = f"Hello {ticket.student_name},\n\nWelcome aboard! This is a confirmation email for your booking for bus service.\n\nYour booking details are as follows:"

        if ticket.pickup_bus_record:
            message += f"\n\nPickup Bus: {ticket.pickup_bus_record.label}"
        if ticket.pickup_schedule:
            message += f"\nPickup Schedule: {ticket.pickup_schedule.name}"
        if ticket.pickup_point:
            message += f"\nPickup Point: {ticket.pickup_point}"

        if ticket.drop_bus_record:
            message += f"\n\nDrop Bus: {ticket.drop_bus_record.label}"
        if ticket.drop_schedule:
            message += f"\nDrop Schedule: {ticket.drop_schedule.name}"
        if ticket.drop_point:
            message += f"\nDrop Point: {ticket.drop_point}"

        message += (
            f"\n\nPlease make sure to be on time at the pickup point."
            f"\n\nIn case of any issues, please contact your respective institution."
            f"\n\nYour ticket ID is: {ticket.ticket_id}"
            f"\n\nBest regards,\nSFSBusNest Team"
        )
        recipient_list = [f"{ticket.student_email}"]
        send_email_task.delay(subject, message, recipient_list)
        
        self.request.session['success_message'] = f"Bus ticket successfully booked for {ticket.student_name}."
        self.request.session['registration_code'] = self.kwargs.get('registration_code')

        return HttpResponseRedirect(reverse('students:book_success', kwargs={'registration_code':registration.code}))
    

class BusBookingSuccessView(TemplateView):
    """
    View to display a success message after a bus ticket is booked.
    """
    template_name = 'students/bus_booking_success.html'
    
    def get_context_data(self, **kwargs):
        """
        Adds booking success message and registration to the context.
        """
        context = super().get_context_data(**kwargs)
        message = self.request.session.get('success_message')
        registration = get_object_or_404(Registration, code=self.request.session.get('registration_code'))
        context['message'] = message
        context['registration'] = registration
        return context
    

class PickupStopSelectFormView(RegistrationOpenCheckMixin, FormView):
    """
    View for students to select a pickup stop for one-way or two-way bookings.
    """
    template_name = 'students/pickup_stop_search_form.html'
    form_class = StopSelectForm

    def get_registration(self):
        """
        Fetch registration using the code from the URL.
        """
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)
    
    def get_form(self, form_class=None):
        """
        Customizes the form's queryset for pickup stops based on selected schedule group.
        Only shows stops that are available in routes for the pickup schedule.
        """
        form = super().get_form(form_class)
        registration = self.get_registration()
        
        # Get the selected schedule group from session
        schedule_group_id = self.request.session.get('schedule_group_id')
        pickup_schedule_id = self.request.session.get('pickup')
        
        if schedule_group_id and pickup_schedule_id:
            schedule_group = get_object_or_404(ScheduleGroup, id=schedule_group_id)
            
            # Get all routes that have trips for the pickup schedule
            # AND are associated with the pickup schedule in route.schedules
            route_ids = Trip.objects.filter(
                schedule_id=int(pickup_schedule_id),
                registration=registration,
                route__schedules__id=int(pickup_schedule_id)  # Additional check: route must be associated with schedule
            ).values_list('route_id', flat=True).distinct()
            
            # Filter stops to only those in the relevant routes
            form.fields['stop'].queryset = Stop.objects.filter(
                registration=registration,
                route_id__in=route_ids
            ).order_by('name').distinct()
        else:
            # Fallback: show all stops if no schedule group selected
            form.fields['stop'].queryset = registration.stops.all().order_by('name')
        
        return form
    
    def get_context_data(self, **kwargs):
        """
        Adds registration to the context for the template.
        """
        context = super().get_context_data(**kwargs)
        context['registration'] = self.get_registration()
        return context

    def form_valid(self, form):
        """
        Stores the selected pickup stop in the session and proceeds to the next step.
        """
        stop = form.cleaned_data['stop']
        self.request.session['pickup_stop_id'] = stop.id
        return super().form_valid(form)

    def get_success_url(self):
        """
        Returns the URL for pickup bus selection after stop selection.
        """
        registration_code = self.get_registration().code
        return reverse('students:pickup_bus_select', kwargs={'registration_code': registration_code})
    

class PickupBusSearchResultsView(RegistrationOpenCheckMixin, ListView):
    """
    View to display available pickup buses for the selected stop and schedule group.
    """
    template_name = 'students/pickup_bus_results.html'
    context_object_name = 'buses'

    def get_queryset(self):
        """
        Returns queryset of pickup buses filtered by selected schedule(s) and stop.
        """
        # Retrieve the registration based on the registration code
        registration_code = self.kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)

        # Get pickup point, drop point, and schedule from session
        stop_id = self.request.session.get('pickup_stop_id')
        schedule_group_id = self.request.session.get('schedule_group_id')
        pickup = self.request.session.get('pickup')
        drop = self.request.session.get('drop')
        

        schedule_group = ScheduleGroup.objects.get(id=int(schedule_group_id))
        
        
        schedule_ids = [schedule_group.pick_up_schedule.id, schedule_group.drop_schedule.id]
        
        if schedule_group.allow_one_way:
            if pickup and drop:
                schedule_ids = [int(pickup)]

        buses = get_filtered_bus_records(schedule_ids, int(stop_id))

        return buses
    
    def get(self, request, *args, **kwargs):
        """
        Redirects to 'bus_not_found' if no buses are found, otherwise renders results.
        """
        self.object_list = self.get_queryset()
        if not self.object_list:
            registration_code = self.kwargs.get('registration_code')
            return HttpResponseRedirect(reverse('students:bus_not_found', kwargs={'registration_code': registration_code}))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Include additional context like the registration."""
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context

class DropStopSelectFormView(RegistrationOpenCheckMixin, FormView):
    """
    View for students to select a drop stop for one-way or two-way bookings.
    """
    template_name = 'students/drop_stop_search_form.html'
    form_class = StopSelectForm

    def get_registration(self):
        """
        Fetch registration using the code from the URL.
        """
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)
    
    def get_form(self, form_class=None):
        """
        Customizes the form's queryset for drop stops based on selected schedule group.
        Only shows stops that are available in routes for the drop schedule.
        """
        form = super().get_form(form_class)
        registration = self.get_registration()
        
        # Get the selected schedule group from session
        schedule_group_id = self.request.session.get('schedule_group_id')
        drop_schedule_id = self.request.session.get('drop')
        
        if schedule_group_id and drop_schedule_id:
            schedule_group = get_object_or_404(ScheduleGroup, id=schedule_group_id)
            
            # Get all routes that have trips for the drop schedule
            # AND are associated with the drop schedule in route.schedules
            route_ids = Trip.objects.filter(
                schedule_id=int(drop_schedule_id),
                registration=registration,
                route__schedules__id=int(drop_schedule_id)  # Additional check: route must be associated with schedule
            ).values_list('route_id', flat=True).distinct()
            
            # Filter stops to only those in the relevant routes
            form.fields['stop'].queryset = Stop.objects.filter(
                registration=registration,
                route_id__in=route_ids
            ).order_by('name').distinct()
        else:
            # Fallback: show all stops if no schedule group selected
            form.fields['stop'].queryset = registration.stops.all().order_by('name')
        
        return form
    
    def get_context_data(self, **kwargs):
        """
        Adds registration to the context for the template.
        """
        context = super().get_context_data(**kwargs)
        context['registration'] = self.get_registration()
        return context

    def form_valid(self, form):
        """
        Stores the selected drop stop in the session and proceeds to the next step.
        """
        stop = form.cleaned_data['stop']
        self.request.session['drop_stop_id'] = stop.id
        registration_code = self.get_registration().code
        pickup_bus = self.request.GET.get('pickup_bus')
        return HttpResponseRedirect(reverse('students:drop_bus_select', kwargs={'registration_code': registration_code}) + f"?pickup_bus={pickup_bus}")


class DropBusSearchResultsView(RegistrationOpenCheckMixin, ListView):
    """
    View to display available drop buses for the selected stop and schedule group.
    """
    template_name = 'students/drop_bus_results.html'
    context_object_name = 'buses'

    def get_queryset(self):
        """
        Returns queryset of drop buses filtered by selected schedule(s) and stop.
        """
        # Retrieve the registration based on the registration code
        registration_code = self.kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)

        stop_id = self.request.session.get('drop_stop_id')
        schedule_group_id = self.request.session.get('schedule_group_id')
        pickup = self.request.session.get('pickup')
        drop = self.request.session.get('drop')
        

        schedule_group = ScheduleGroup.objects.get(id=int(schedule_group_id))
        
        
        schedule_ids = [schedule_group.pick_up_schedule.id, schedule_group.drop_schedule.id]
        
        if schedule_group.allow_one_way:
            if pickup and drop:
                schedule_ids = [int(drop)]

        buses = get_filtered_bus_records(schedule_ids, int(stop_id))

        return buses
    
    def get(self, request, *args, **kwargs):
        """
        Redirects to 'bus_not_found' if no buses are found, otherwise renders results.
        """
        self.object_list = self.get_queryset()
        if not self.object_list:
            registration_code = self.kwargs.get('registration_code')
            return HttpResponseRedirect(reverse('students:bus_not_found', kwargs={'registration_code': registration_code}))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Include additional context like the registration."""
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        context['pickup_bus_record_slug'] = self.request.GET.get('pickup_bus')
        return context

