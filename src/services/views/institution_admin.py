from django.shortcuts import redirect
from django.views.generic import FormView, ListView, CreateView
from django.urls import reverse
from services.models import Registration, Receipt, StudentGroup

class RegistrationListView(ListView):
    model = Registration
    template_name = 'institution_admin/registration_list.html'
    context_object_name = 'registrations'


class ReceiptListView(ListView):
    model = Receipt
    template_name = 'institution_admin/receipt_list.html'
    context_object_name = 'receipts'
    
    
class ReceiptCreateView(CreateView):
    template_name = 'institution_admin/receipt_create.html'
    model = Receipt
    fields = ['registration', 'receipt_id', 'student_id', 'student_group', 'institution']
    
    def form_valid(self, form):
        receipt = form.save(commit=False)
        user = self.request.user
        receipt.org = user.profile.org
        receipt.save()
        return redirect('institution_admin:receipt_list')
    
    
class StudentGroupListView(ListView):
    model = StudentGroup
    template_name = 'institution_admin/student_group_list.html'
    context_object_name = 'student_groups'  
    
    
class StudentGroupCreateView(CreateView):
    template_name = 'institution_admin/student_group_create.html'
    model = StudentGroup
    fields = ['name', 'institution']
    
    def form_valid(self, form):
        receipt = form.save(commit=False)
        user = self.request.user
        receipt.org = user.profile.org
        receipt.save()
        return redirect('institution_admin:student_group_list') 
    
    