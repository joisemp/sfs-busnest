from django.shortcuts import redirect
from django.views.generic import FormView, ListView, CreateView, DeleteView, UpdateView
from django.urls import reverse, reverse_lazy
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
    fields = ['registration', 'receipt_id', 'student_id', 'student_group']
    
    def form_valid(self, form):
        receipt = form.save(commit=False)
        user = self.request.user
        receipt.org = user.profile.org
        receipt.institution = user.profile.institution
        receipt.save()
        return redirect('institution_admin:receipt_list')
    

class ReceiptDeleteView(DeleteView):
    model = Receipt
    template_name = 'institution_admin/receipt_confirm_delete.html'
    slug_url_kwarg = 'receipt_slug'
    success_url = reverse_lazy('institution_admin:receipt_list')
    
    
class StudentGroupListView(ListView):
    model = StudentGroup
    template_name = 'institution_admin/student_group_list.html'
    context_object_name = 'student_groups'  
    
    
class StudentGroupCreateView(CreateView):
    template_name = 'institution_admin/student_group_create.html'
    model = StudentGroup
    fields = ['name',]
    
    def form_valid(self, form):
        receipt = form.save(commit=False)
        user = self.request.user
        receipt.org = user.profile.org
        receipt.institution = user.profile.institution
        receipt.save()
        return redirect('institution_admin:student_group_list') 
    
    
class StudentGroupUpdateView(UpdateView):
    model = StudentGroup
    fields = ['name',]
    template_name = 'institution_admin/student_group_update.html'
    slug_url_kwarg = 'student_group_slug'
    success_url = reverse_lazy('institution_admin:student_group_list')

    def form_valid(self, form):
        return super().form_valid(form)
    
    