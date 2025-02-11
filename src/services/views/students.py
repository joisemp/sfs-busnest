from django.db import transaction
from django.http import HttpResponseRedirect
from django.views.generic import FormView, ListView, CreateView, TemplateView, View
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from services.forms.students import StopSelectForm, ValidateStudentForm, TicketForm, BusRequestForm
from services.models import Registration, ScheduleGroup, Ticket, Schedule, Receipt, BusRequest, BusRecord, Trip
from config.mixins.access_mixin import RegistrationOpenCheckMixin
from services.utils import get_filtered_bus_records

class ValidateStudentFormView(RegistrationOpenCheckMixin, FormView):
    template_name = 'students/validate_student_form.html'
    form_class = ValidateStudentForm  
    
    def form_valid(self, form):
        try:
            receipt_id = form.cleaned_data['receipt_id']
            student_id = form.cleaned_data['student_id']
            
            # Validate receipt
            receipt = Receipt.objects.get(receipt_id=receipt_id, student_id=student_id)

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
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    
    def get_success_url(self):
        registration_code = self.kwargs.get('registration_code')
        return reverse('students:rules_and_regulations', kwargs={'registration_code': registration_code})
    

class RulesAndRegulationsView(RegistrationOpenCheckMixin, TemplateView):
    template_name = 'students/rules_and_regulations.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context


class StopSelectFormView(RegistrationOpenCheckMixin, FormView):
    template_name = 'students/search_form.html'
    form_class = StopSelectForm

    def get_registration(self):
        """Fetch registration using the code from the URL."""
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        registration = self.get_registration()
        form.fields['stop'].queryset = registration.stops.all()
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.get_registration()
        return context

    def form_valid(self, form):
        stop = form.cleaned_data['stop']
        self.request.session['stop_id'] = stop.id
        return super().form_valid(form)

    def get_success_url(self):
        registration_code = self.get_registration().code
        return reverse('students:schedule_group_select', kwargs={'registration_code': registration_code})
    

class SelectScheduleGroupView(RegistrationOpenCheckMixin, View):
    template_name = 'students/select_schedule_group.html'

    def get(self, request, registration_code):
        schedule_groups = ScheduleGroup.objects.all()
        return render(request, self.template_name, {'schedule_groups': schedule_groups})

    def post(self, request, registration_code):
        selected_id = request.POST.get("schedule_group")
        pickup = request.POST.get(f"pickup_{selected_id}")  # Checkbox value
        drop = request.POST.get(f"drop_{selected_id}")  # Checkbox value

        if not selected_id:
            schedule_groups = ScheduleGroup.objects.all()
            return render(
                request,
                self.template_name,
                {
                    'schedule_groups': schedule_groups,
                    'error_message': "Please select a schedule group.",
                }
            )

        selected_group = ScheduleGroup.objects.get(id=selected_id)
        
        # Process the selection
        selection_details = {
            "selected_group": selected_group,
            "pickup": pickup,
            "drop": drop
        }
        
        self.request.session['schedule_group_id'] = selection_details['selected_group'].id
        self.request.session['pickup'] = selection_details['pickup']
        self.request.session['drop'] = selection_details['drop']

        return HttpResponseRedirect(reverse('students:bus_search_results', kwargs={'registration_code': registration_code}))


class BusSearchResultsView(RegistrationOpenCheckMixin, ListView):
    template_name = 'students/search_results.html'
    context_object_name = 'buses'

    def get_queryset(self):
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
    template_name = 'students/bus_not_found.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    

class BusRequestFormView(RegistrationOpenCheckMixin, CreateView):
    model = BusRequest
    template_name = 'students/bus_request.html'
    form_class = BusRequestForm
    
    @transaction.atomic
    def form_valid(self, form):
        bus_request = form.save(commit=False)
        registration = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        receipt = get_object_or_404(Receipt, id=self.request.session.get('receipt_id'))
        bus_request.org = registration.org
        bus_request.registration = registration
        bus_request.receipt = receipt
        bus_request.institution = receipt.institution
        bus_request.student_group = receipt.student_group
        bus_request.save()
        return HttpResponseRedirect(reverse('students:bus_request_success', kwargs={'registration_code':registration.code}))
    

class BusRequestSuccessView(RegistrationOpenCheckMixin, TemplateView):
    template_name = 'students/bus_request_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    

class BusBookingView(RegistrationOpenCheckMixin, CreateView):
    model = Ticket
    template_name = 'students/bus_booking.html'
    form_class = TicketForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        self.bus_record = get_object_or_404(BusRecord, slug=self.kwargs.get('bus_slug'))
        self.schedule_group_id = self.request.session.get('schedule_group_id')
        self.pickup_id = self.request.session.get('pickup')
        self.drop_id = self.request.session.get('drop')
        
        self.schedule_group = ScheduleGroup.objects.get(id=int(self.schedule_group_id))
        
        
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
                pickup_trip = Trip.objects.get(record=self.bus_record, schedule=self.schedule_group.pick_up_schedule)
                drop_trip = Trip.objects.get(record=self.bus_record, schedule=self.schedule_group.drop_schedule)
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
        ticket = form.save(commit=False)
        registration = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        receipt_id = self.request.session.get('receipt_id')
        std_id = self.request.session.get('student_id')
        receipt = get_object_or_404(Receipt, id=receipt_id)

        ticket.org = registration.org
        ticket.registration = registration
        ticket.institution = receipt.institution
        ticket.student_group = receipt.student_group
        ticket.recipt = receipt
        ticket.student_id = std_id

        try:
            pickup_trip = Trip.objects.get(record=self.bus_record, schedule=self.schedule_group.pick_up_schedule)
            if 'pickup_point' in form.fields:
                form.fields['pickup_point'].queryset = pickup_trip.route.stops.all()
        except Trip.DoesNotExist:
            pickup_trip = None

        try:
            drop_trip = Trip.objects.get(record=self.bus_record, schedule=self.schedule_group.drop_schedule)
            if 'drop_point' in form.fields:
                form.fields['drop_point'].queryset = drop_trip.route.stops.all()
        except Trip.DoesNotExist:
            drop_trip = None

        if self.schedule_group.allow_one_way:
            if self.pickup_id and not self.drop_id:  # One-way pickup only
                ticket.pickup_bus_record = self.bus_record
                ticket.pickup_schedule = self.schedule_group.pick_up_schedule
                if pickup_trip:
                    pickup_trip.booking_count += 1
                ticket.ticket_type = 'one_way'

            elif self.drop_id and not self.pickup_id:  # One-way drop only
                ticket.drop_bus_record = self.bus_record
                ticket.drop_schedule = self.schedule_group.drop_schedule
                if drop_trip:
                    drop_trip.booking_count += 1
                ticket.ticket_type = 'one_way'

            else:  # Both pickup and drop (two-way)
                ticket.pickup_bus_record = self.bus_record
                ticket.drop_bus_record = self.bus_record
                ticket.pickup_schedule = self.schedule_group.pick_up_schedule
                ticket.drop_schedule = self.schedule_group.drop_schedule
                if pickup_trip:
                    pickup_trip.booking_count += 1
                if drop_trip:
                    drop_trip.booking_count += 1
                ticket.ticket_type = 'two_way'
        else:
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
        
        self.request.session['success_message'] = f"Bus ticket successfully booked for {ticket.student_name}."
        self.request.session['registration_code'] = self.kwargs.get('registration_code')

        return redirect('students:book_success')
    

class BusBookingSuccessView(TemplateView):
    template_name = 'students/bus_booking_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        message = self.request.session.get('success_message')
        registration = get_object_or_404(Registration, code=self.request.session.get('registration_code'))
        context['message'] = message
        context['registration'] = registration
        return context

        