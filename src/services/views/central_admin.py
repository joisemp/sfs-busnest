from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from services.models import Institution


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
        institution.user = user
        institution.save()
        return redirect('central_admin:institution_list')
        
