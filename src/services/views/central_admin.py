from django.shortcuts import render
from django.views.generic import ListView
from services.models import Institution


class InstitutionListView(ListView):
    template_name = 'central_admin/institution_list.html'
    model = Institution
    context_object_name = 'institutions'
    
    
