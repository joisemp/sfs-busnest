from django.db import transaction
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect
from django.views.generic import FormView, ListView, CreateView, TemplateView, View
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from services.forms.students import StopSelectForm, ValidateStudentForm, TicketForm, BusRequestForm
from services.models import Registration, ScheduleGroup, Ticket, Schedule, Receipt, BusRequest, BusRecord
from django.db.models import F, Q, Count
from services.tasks import send_email_task
from services.utils import get_filtered_bus_records

class ValidateStudentFormView(FormView):
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
    

class RulesAndRegulationsView(TemplateView):
    template_name = 'students/rules_and_regulations.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context


class StopSelectFormView(FormView):
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

    def form_valid(self, form):
        stop = form.cleaned_data['stop']
        self.request.session['stop_id'] = stop.id
        return super().form_valid(form)

    def get_success_url(self):
        registration_code = self.get_registration().code
        return reverse('students:schedule_group_select', kwargs={'registration_code': registration_code})
    

class SelectScheduleGroupView(View):
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


class BusSearchResultsView(ListView):
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


class BusNotFoundView(TemplateView):
    template_name = 'students/bus_not_found.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    

class BusRequestFormView(CreateView):
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
    

class BusRequestSuccessView(TemplateView):
    template_name = 'students/bus_request_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    

class BusBookingView(CreateView):
    model = Ticket
    template_name = 'students/bus_booking.html'
    form_class = TicketForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        self.bus_record = get_object_or_404(BusRecord, slug=self.kwargs.get('bus_slug'))
        form.fields['stop'].queryset = self.bus_record.route.stops.all()
        return form
    
    @transaction.atomic
    def form_valid(self, form):
        ticket = form.save(commit=False)
        registration = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        stop=form.cleaned_data.get('stop')
        receipt_id = self.request.session.get('receipt_id')
        std_id = self.request.session.get('student_id')
        schedule_id = self.request.session.get('schedule')
        receipt = get_object_or_404(Receipt, id=receipt_id)
        
        ticket.pickup_point = stop
        ticket.drop_point = stop
        ticket.recipt = receipt
        ticket.student_id = std_id
        ticket.student_group = receipt.student_group
        ticket.institution = receipt.institution
        ticket.schedule = get_object_or_404(Schedule, id=schedule_id)
        ticket.registration = registration
        ticket.org = registration.org
        ticket.pickup_bus_record = self.bus_record
        ticket.drop_bus_record = self.bus_record
        ticket.status = True
        
        self.bus_record.pickup_booking_count += 1
        self.bus_record.drop_booking_count += 1
        
        self.bus_record.save()
        ticket.save()
        
        subject = "Booking Confirmation"
        message = (
            f"Hello {ticket.student_name},\n\n"
            f"Welcome aboard! This is an confirmation email for your booking for {ticket.pickup_bus_record.label} from {ticket.pickup_point.name}"
            f"\nIncase of any issues please contact your respective insitution"
            f"\n\nYour ticket id is : {ticket.ticket_id}"
            f"\n\nBest regards,\nSFSBusNest Team"
            )
        recipient_list = [f"{ticket.student_email}"]
        send_email_task.delay(subject, message, recipient_list)
        
        self.request.session['ticket_id'] = ticket.id
        
        return redirect('students:book_success')
    

class BusBookingSuccessView(TemplateView):
    template_name = 'students/bus_booking_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket = get_object_or_404(Ticket, id=self.request.session.get('ticket_id'))
        context['ticket'] = ticket
        return context

        