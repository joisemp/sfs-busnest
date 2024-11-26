from django.views.generic import FormView, ListView, CreateView
from django.urls import reverse
from services.models import Registration, Recipt, StudentGroup

class RegistrationListView(ListView):
    model = Registration
    template_name = 'institution_admin/registration_list.html'
    context_object_name = 'registrations'


class ReciptListView(ListView):
    model = Recipt
    template_name = 'institution_admin/recipt_list.html'
    context_object_name = 'recipts'
    
    
class StudentGroupListView(ListView):
    model = StudentGroup
    template_name = 'institution_admin/student_group_list.html'
    context_object_name = 'student_groups'   
    
    