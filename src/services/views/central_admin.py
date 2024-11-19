from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from services.models import Institution, Bus, Stop, Route, Registration
from core.models import UserProfile
from django.db import transaction
from django.contrib.auth.base_user import BaseUserManager
from config.utils import generate_unique_code
from django.contrib.auth import get_user_model

from services.forms.central_admin import PeopleCreateForm, PeopleUpdateForm


User = get_user_model()


class InstitutionListView(ListView):
    template_name = 'central_admin/institution_list.html'
    model = Institution
    context_object_name = 'institutions'
    

class InstitutionCreateView(CreateView):
    template_name = 'central_admin/institution_create.html'
    model = Institution
    fields = ['name', 'label', 'contact_no', 'email', 'incharge']
    
    def form_valid(self, form):
        institution = form.save(commit=False)
        user = self.request.user
        institution.org = user.profile.org
        institution.save()
        return redirect('central_admin:institution_list')
    

class InstitutionUpdateView(UpdateView):
    model = Institution
    fields = ['name', 'label', 'contact_no', 'email', 'incharge']
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
    fields = ['label', 'bus_no', 'driver']
    
    def form_valid(self, form):
        bus = form.save(commit=False)
        user = self.request.user
        bus.org = user.profile.org
        bus.save()
        return redirect('central_admin:bus_list')
    
    
class BusUpdateView(UpdateView):
    model = Bus
    fields = ['label', 'bus_no', 'driver']
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
    fields = ['name', 'stops']
    
    def form_valid(self, form):
        route = form.save(commit=False)
        user = self.request.user
        route.org = user.profile.org
        route.save()
        return redirect('central_admin:route_list')
    
    
class RouteUpdateView(UpdateView):
    model = Route
    fields = ['name', 'stops']
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
    fields = ['name', 'map_link']
    
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
    fields = ['name', 'instructions', 'stops', 'status']
    
    def form_valid(self, form):
        registration = form.save(commit=False)
        user = self.request.user
        registration.org = user.profile.org
        registration.code = generate_unique_code(Registration)
        registration.save()
        return redirect('central_admin:registrations_list')
    
    