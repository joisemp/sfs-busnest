from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from services.models import Institution, Bus, Stop, Route, Registration, Ticket, FAQ
from core.models import UserProfile
from django.db import transaction
from django.contrib.auth.base_user import BaseUserManager
from config.utils import generate_unique_code
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import Http404

from services.forms.central_admin import PeopleCreateForm, PeopleUpdateForm, InstitutionForm, BusForm, RouteForm, StopForm, RegistrationForm, FAQForm


User = get_user_model()


class InstitutionListView(ListView):
    template_name = 'central_admin/institution_list.html'
    model = Institution
    context_object_name = 'institutions'
    

class InstitutionCreateView(CreateView):
    template_name = 'central_admin/institution_create.html'
    model = Institution
    form_class = InstitutionForm
    
    def form_valid(self, form):
        institution = form.save(commit=False)
        user = self.request.user
        institution.org = user.profile.org
        institution.save()
        return redirect('central_admin:institution_list')
    

class InstitutionUpdateView(UpdateView):
    model = Institution
    form_class = InstitutionForm
    template_name = 'central_admin/institution_update.html'
    success_url = reverse_lazy('central_admin:institution_list')

    def form_valid(self, form):
        return super().form_valid(form)


class InstitutionDeleteView(DeleteView):
    model = Institution
    template_name = 'central_admin/institution_confirm_delete.html'
    success_url = reverse_lazy('central_admin:institution_list')


class BusListView(ListView):
    model = Bus
    template_name = 'central_admin/bus_list.html'
    context_object_name = 'buses'


class BusCreateView(CreateView):
    template_name = 'central_admin/bus_create.html'
    model = Bus
    form_class = BusForm
    
    def form_valid(self, form):
        bus = form.save(commit=False)
        user = self.request.user
        bus.org = user.profile.org
        bus.save()
        return redirect('central_admin:bus_list')
    
    
class BusUpdateView(UpdateView):
    model = Bus
    form_class = BusForm
    template_name = 'central_admin/bus_update.html'
    success_url = reverse_lazy('central_admin:bus_list')

    def form_valid(self, form):
        return super().form_valid(form)


class BusDeleteView(DeleteView):
    model = Bus
    template_name = 'central_admin/bus_confirm_delete.html'
    success_url = reverse_lazy('central_admin:bus_list')
    
    
class PeopleListView(ListView):
    model = UserProfile
    template_name = 'central_admin/people_list.html'
    context_object_name = 'people'
    

class PeopleCreateView(CreateView):
    model = UserProfile
    template_name = 'central_admin/people_create.html'
    form_class = PeopleCreateForm
    success_url = reverse_lazy('central_admin:people_list')

    @transaction.atomic
    def form_valid(self, form):
        try:
            userprofile = form.save(commit=False)

            random_password = BaseUserManager().make_random_password()

            user = User.objects.create_user(
                email=form.cleaned_data.get('email'),
                first_name=userprofile.first_name,
                last_name=userprofile.last_name,
                password=random_password,
            )

            userprofile.user = user
            userprofile.org = self.request.user.profile.org
            userprofile.save()
            
            return redirect(self.success_url)
        except Exception as e:
            print(self.request, f"An error occurred: {str(e)}")
            return self.form_invalid(form)
        
        
class PeopleUpdateView(UpdateView):
    model = UserProfile
    form_class = PeopleUpdateForm
    template_name = 'central_admin/people_update.html'
    success_url = reverse_lazy('central_admin:people_list')

    def form_valid(self, form):
        return super().form_valid(form)
    

class PeopleDeleteView(DeleteView):
    model = UserProfile
    template_name = 'central_admin/people_confirm_delete.html'
    success_url = reverse_lazy('central_admin:people_list')


class RouteListView(ListView):
    model = Route
    template_name = 'central_admin/route_list.html'
    context_object_name = 'routes'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stops"] = Stop.objects.all()
        return context
        

class RouteCreateView(CreateView):
    template_name = 'central_admin/route_create.html'
    model = Route
    form_class = RouteForm
    
    def form_valid(self, form):
        route = form.save(commit=False)
        user = self.request.user
        route.org = user.profile.org
        route.save()
        form.save_m2m()
        return redirect('central_admin:route_list')
    
    
class RouteUpdateView(UpdateView):
    model = Route
    form_class = RouteForm
    template_name = 'central_admin/route_update.html'
    success_url = reverse_lazy('central_admin:route_list')

    def form_valid(self, form):
        return super().form_valid(form)
    
    
class RouteDeleteView(DeleteView):
    model = Route
    template_name = 'central_admin/route_confirm_delete.html'
    success_url = reverse_lazy('central_admin:route_list')
    

class StopCreateView(CreateView):
    template_name = 'central_admin/stop_create.html'
    model = Stop
    form_class = StopForm
    
    def form_valid(self, form):
        stop = form.save(commit=False)
        user = self.request.user
        stop.org = user.profile.org
        stop.save()
        return redirect('central_admin:route_list')
    

class StopDeleteView(DeleteView):
    model = Stop
    template_name = 'central_admin/stop_confirm_delete.html'
    success_url = reverse_lazy('central_admin:route_list')


class RegistraionListView(ListView):
    model = Registration
    template_name = 'central_admin/registration_list.html'
    context_object_name = 'registrations'
    
    
class RegistrationCreateView(CreateView):
    template_name = 'central_admin/registration_create.html'
    model = Registration
    form_class = RegistrationForm
    
    def form_valid(self, form):
        registration = form.save(commit=False)
        user = self.request.user
        registration.org = user.profile.org
        registration.code = generate_unique_code(Registration)
        registration.save()
        return redirect('central_admin:registration_list')
    
    
class RegistrationDetailView(DetailView):
    template_name = 'central_admin/registration_detail.html'
    model = Registration
    context_object_name = 'registration'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tickets = self.object.tickets.all().order_by('-created_at')  # Get all tickets for the registration
        
        # Pagination logic
        paginator = Paginator(tickets, 10)  # Show 10 tickets per page
        page_number = self.request.GET.get('page', 1)  # Get page number from query params
        try:
            page_obj = paginator.get_page(page_number)
        except:
            raise Http404("Invalid page number")
        
        context['page_obj'] = page_obj
        context['paginator'] = paginator
        
        # Assuming each Registration object has related tickets
        context['recent_tickets'] = self.object.tickets.all().order_by('-created_at')[:20]
        return context


class RegistrationUpdateView(UpdateView):
    model = Registration
    form_class = RegistrationForm
    template_name = 'central_admin/registration_update.html'

    def form_valid(self, form):
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faq_form'] = FAQForm
        return context
    
    def get_success_url(self):
        return reverse('central_admin:registration_detail', kwargs={'slug': self.kwargs['slug']})
    

class RegistrationDeleteView(DeleteView):
    model = Registration
    template_name = 'central_admin/registration_confirm_delete.html'
    success_url = reverse_lazy('central_admin:registration_list')
    
    
class TicketListView(ListView):
    model = Ticket
    template_name = 'central_admin/ticket_list.html'
    context_object_name = 'tickets'
    
    def get_queryset(self):
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)
        return Ticket.objects.filter(registration=self.registration).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.registration
        return context
    

class FAQCreateView(CreateView):
    template_name = 'central_admin/registration_create.html'
    model = FAQ
    form_class = FAQForm
    
    def form_valid(self, form):
        faq = form.save(commit=False)
        user = self.request.user
        faq.org = user.profile.org
        faq.registration = get_object_or_404(Registration, slug=self.kwargs['registration_slug'])
        faq.save()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('central_admin:registration_update', kwargs={'slug': self.kwargs['registration_slug']})
    
    
class FAQDeleteView(DeleteView):
    model = FAQ
    template_name = 'central_admin/registration_confirm_delete.html'
    slug_url_kwarg = 'faq_slug'
    
    def get_success_url(self):
        return reverse('central_admin:registration_update', kwargs={'slug': self.kwargs['registration_slug']})
