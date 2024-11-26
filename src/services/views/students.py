from django.db import transaction
from django.views.generic import FormView, ListView, CreateView, TemplateView
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from services.forms.students import BusSearchForm, ValidateStudentForm, TicketForm
from services.models import Registration, Bus, Ticket, TimeSlot
from django.db.models import Q, Count

class BusSearchFormView(FormView):
    template_name = 'students/search_form.html'
    form_class = BusSearchForm

    def get_registration(self):
        """Fetch registration using the code from the URL."""
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)

    def form_valid(self, form):
        registration = self.get_registration()
        pickup_point = form.cleaned_data['pickup_point']
        drop_point = form.cleaned_data['drop_point']
        time_slot = form.cleaned_data['time_slot']

        # Store search criteria in the session for passing to results view
        self.request.session['pickup_point'] = pickup_point.id
        self.request.session['drop_point'] = drop_point.id
        self.request.session['time_slot'] = time_slot.id

        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context

    def get_success_url(self):
        registration_code = self.kwargs.get('registration_code')
        return reverse('students:bus_search_results', kwargs={'registration_code': registration_code})


class BusSearchResultsView(ListView):
    template_name = 'students/search_results.html'
    context_object_name = 'buses'

    def get_queryset(self):
        registration_code = self.kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)

        pickup_point_id = self.request.session.get('pickup_point')
        drop_point_id = self.request.session.get('drop_point')
        time_slot_id = self.request.session.get('time_slot')

        if not (pickup_point_id and drop_point_id and time_slot_id):
            return Bus.objects.none()
        
        buses = Bus.objects.filter(
            org=registration.org,
            time_slot_id=time_slot_id,
        ).filter(
            Q(route__stops__id=pickup_point_id) if pickup_point_id == drop_point_id else Q(route__stops__id__in=[pickup_point_id, drop_point_id])
        ).annotate(
            matching_stops=Count('route__stops', filter=Q(route__stops__id__in=[pickup_point_id, drop_point_id]))
        ).filter(
            matching_stops=1 if pickup_point_id == drop_point_id else 2
        ).distinct()

        return buses

    def get_context_data(self, **kwargs):
        """Include additional context like the registration."""
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    
 
class ValidateStudentFormView(FormView):
    template_name = 'students/validate_student_form.html'
    form_class = ValidateStudentForm  
    
    def form_valid(self, form):
        recipt_id = form.cleaned_data['recipt_id']
        student_id = form.cleaned_data['student_id']

        # Store search criteria in the session
        self.request.session['recipt_id'] = recipt_id
        self.request.session['student_id'] = student_id
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context
    
    def get_success_url(self):
        registration_code = self.kwargs.get('registration_code')
        bus_slug = self.kwargs.get('bus_slug')
        return reverse('students:book_bus', kwargs={'bus_slug':bus_slug, 'registration_code': registration_code})


class BusBookingView(CreateView):
    model = Ticket
    template_name = 'students/bus_booking.html'
    form_class = TicketForm
    
    @transaction.atomic
    def form_valid(self, form):
        ticket = form.save(commit=False)
        registration = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        bus = get_object_or_404(Bus, slug=self.kwargs.get('bus_slug'))
        stop=form.cleaned_data.get('stop')
        recipt_id = self.request.session.get('recipt_id')
        std_id = self.request.session.get('student_id')
        time_slot_id = self.request.session.get('time_slot')
        
        ticket.pickup_point = stop
        ticket.drop_point = stop
        ticket.recipt_id = recipt_id
        ticket.student_id = std_id
        ticket.time_slot = get_object_or_404(TimeSlot, id=time_slot_id)
        ticket.registration = registration
        ticket.org = registration.org
        ticket.status = True
        ticket.bus = bus
        ticket.save()
        
        self.request.session['ticket_id'] = ticket.id
        
        return redirect('students:book_success')
    

class BusBookingSuccessView(TemplateView):
    template_name = 'students/bus_booking_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = get_object_or_404(Ticket, id=self.request.session.get('ticket_id'))
        return context

        