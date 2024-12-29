from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, CreateView, DeleteView, UpdateView
from django.urls import reverse, reverse_lazy
from services.models import Registration, Receipt, Stop, StudentGroup, Ticket, TimeSlot, ReceiptFile
from services.forms.institution_admin import ReceiptForm, StudentGroupForm, TicketForm
from config.mixins.access_mixin import InsitutionAdminOnlyAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from services.tasks import process_uploaded_receipt_data_csv

class RegistrationListView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, ListView):
    model = Registration
    template_name = 'institution_admin/registration_list.html'
    context_object_name = 'registrations'
    
    def get_queryset(self):
        queryset = Registration.objects.filter(org=self.request.user.profile.org)
        return queryset
    

class TicketListView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, ListView):
    model = Ticket
    template_name = 'institution_admin/ticket_list.html'
    context_object_name = 'tickets'
    
    def get_queryset(self):
        # Get registration based on slug
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)
        
        # Base queryset filtered by registration and institution
        queryset = Ticket.objects.filter(registration=self.registration, institution=self.request.user.profile.institution).order_by('-created_at')
        
        # Apply filters based on GET parameters
        pickup_points = self.request.GET.getlist('pickup_point')
        drop_points = self.request.GET.getlist('drop_point')
        time_slot = self.request.GET.get('time_slot')
        student_group = self.request.GET.get('student_group')
        filters = False  # Default no filters applied

        # Apply filters based on GET parameters and update the filters flag
        if pickup_points and not pickup_points == ['']:
            queryset = queryset.filter(pickup_point_id__in=pickup_points)
            filters = True
        if drop_points and not drop_points == ['']:
            queryset = queryset.filter(drop_point_id__in=drop_points)
            filters = True
        if time_slot:
            queryset = queryset.filter(time_slot_id=time_slot)
            filters = True
        if student_group:
            queryset = queryset.filter(student_group_id=student_group)
            filters = True
        
        # Pass the filters flag to context (done in get_context_data)
        self.filters = filters  # Store in the instance for later access

        return queryset
    
    def get_context_data(self, **kwargs):
        # Get default context from parent
        context = super().get_context_data(**kwargs)
        
        # Add the filter status to the context
        context['filters'] = self.filters  # Pass the filters flag to the template
        
        # Add the filter options to the context
        context['registration'] = self.registration
        context['pickup_points'] = Stop.objects.filter(
            org = self.request.user.profile.org
        )
        context['drop_points'] = Stop.objects.filter(
            org = self.request.user.profile.org
        )
        context['time_slots'] = TimeSlot.objects.filter(
            org = self.request.user.profile.org
        )
        context['student_groups'] = StudentGroup.objects.filter(
            org = self.request.user.profile.org,
            institution = self.request.user.profile.institution
        ).order_by('name')

        return context


class TicketUpdateView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, UpdateView):
    model = Ticket
    form_class = TicketForm
    template_name = 'institution_admin/ticket_update.html'
    slug_url_kwarg = 'ticket_slug'

    def form_valid(self, form):
        ticket = form.save()
        
        if ticket.institution != ticket.recipt.institution:
            ticket.recipt.institution = ticket.institution
            ticket.recipt.save()
            
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse(
            'institution_admin:ticket_list', 
            kwargs={'registration_slug': self.kwargs['registration_slug']}
            )


class ReceiptListView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, ListView):
    model = Receipt
    template_name = 'institution_admin/receipt_list.html'
    context_object_name = 'receipts'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Receipt.objects.filter(
            org=self.request.user.profile.org,
            institution=self.request.user.profile.institution
            )
        return queryset
    

class ReceiptDataFileUploadView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, CreateView):
    model = ReceiptFile
    fields = ['registration', 'file']
    template_name = 'institution_admin/receipt_file_upload.html'
    
    def form_valid(self, form):
        receipt_data_file = form.save(commit=False)
        user = self.request.user
        receipt_data_file.org = user.profile.org
        receipt_data_file.institution = user.profile.institution
        receipt_data_file.save()
        process_uploaded_receipt_data_csv.delay(receipt_data_file.file.name, user.profile.org.id, user.profile.institution.id, receipt_data_file.registration.id)
        return redirect('institution_admin:receipt_list')
    
    
class ReceiptCreateView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, CreateView):
    template_name = 'institution_admin/receipt_create.html'
    model = Receipt
    form_class = ReceiptForm
    
    def form_valid(self, form):
        receipt = form.save(commit=False)
        user = self.request.user
        receipt.org = user.profile.org
        receipt.institution = user.profile.institution
        receipt.save()
        return redirect('institution_admin:receipt_list')
    

class ReceiptDeleteView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, DeleteView):
    model = Receipt
    template_name = 'institution_admin/receipt_confirm_delete.html'
    slug_url_kwarg = 'receipt_slug'
    success_url = reverse_lazy('institution_admin:receipt_list')
    
    
class StudentGroupListView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, ListView):
    model = StudentGroup
    template_name = 'institution_admin/student_group_list.html'
    context_object_name = 'student_groups'  
    
    def get_queryset(self):
        queryset = StudentGroup.objects.filter(
            org = self.request.user.profile.org,
            institution = self.request.user.profile.institution
        ).order_by('name')
        return queryset
    
    
class StudentGroupCreateView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, CreateView):
    template_name = 'institution_admin/student_group_create.html'
    model = StudentGroup
    form_class = StudentGroupForm
    
    def form_valid(self, form):
        receipt = form.save(commit=False)
        user = self.request.user
        receipt.org = user.profile.org
        receipt.institution = user.profile.institution
        receipt.save()
        return redirect('institution_admin:student_group_list') 
    
    
class StudentGroupUpdateView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, UpdateView):
    model = StudentGroup
    form_class = StudentGroupForm
    template_name = 'institution_admin/student_group_update.html'
    slug_url_kwarg = 'student_group_slug'
    success_url = reverse_lazy('institution_admin:student_group_list')

    def form_valid(self, form):
        return super().form_valid(form)
    
    
class StudentGroupDeleteView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, DeleteView):
    model = StudentGroup
    template_name = 'institution_admin/student_group_confirm_delete.html'
    slug_url_kwarg = 'student_group_slug'
    success_url = reverse_lazy('institution_admin:student_group_list')
    
    
    