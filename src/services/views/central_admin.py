from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from services.models import Institution, Bus


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
    
        