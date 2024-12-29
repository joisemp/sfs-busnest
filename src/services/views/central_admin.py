from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from services.models import Institution, Bus, Stop, Route, RouteFile, Registration, Ticket, FAQ, TimeSlot
from core.models import UserProfile
from django.db import transaction
from django.contrib.auth.base_user import BaseUserManager
from config.utils import generate_unique_code
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import Http404
from django.db.models import Q
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin

from services.forms.central_admin import PeopleCreateForm, PeopleUpdateForm, InstitutionForm, BusForm, RouteForm, StopForm, RegistrationForm, FAQForm, TimeSlotForm

from services.tasks import process_uploaded_csv, send_email_task


User = get_user_model()


class InstitutionListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    template_name = 'central_admin/institution_list.html'
    model = Institution
    context_object_name = 'institutions'
    
    def get_queryset(self):
        self.search_term = self.request.GET.get('search', '')
        queryset = Institution.objects.filter(org=self.request.user.profile.org)
        if self.search_term:
            queryset = queryset.filter(
                Q(name__icontains=self.search_term) |
                Q(label__icontains=self.search_term) |
                Q(incharge__first_name__icontains=self.search_term) |
                Q(email__icontains=self.search_term)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_term'] = self.search_term
        return context
    

class InstitutionCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/institution_create.html'
    model = Institution
    form_class = InstitutionForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['incharge'].queryset = UserProfile.objects.filter(org=self.request.user.profile.org, is_institution_admin=True)
        return form
    
    def form_valid(self, form):
        institution = form.save(commit=False)
        user = self.request.user
        institution.org = user.profile.org
        institution.save()
        return redirect('central_admin:institution_list')
    

class InstitutionUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = Institution
    form_class = InstitutionForm
    template_name = 'central_admin/institution_update.html'
    success_url = reverse_lazy('central_admin:institution_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['incharge'].queryset = UserProfile.objects.filter(org=self.request.user.profile.org, is_institution_admin=True)
        return form

    def form_valid(self, form):
        return super().form_valid(form)


class InstitutionDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Institution
    template_name = 'central_admin/institution_confirm_delete.html'
    success_url = reverse_lazy('central_admin:institution_list')


class BusListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = Bus
    template_name = 'central_admin/bus_list.html'
    context_object_name = 'buses'
    
    def get_queryset(self):
        queryset = Bus.objects.filter(org=self.request.user.profile.org)
        return queryset


class BusCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/bus_create.html'
    model = Bus
    form_class = BusForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['route'].queryset = Route.objects.filter(org=self.request.user.profile.org)
        form.fields['time_slot'].queryset = TimeSlot.objects.filter(org=self.request.user.profile.org)
        return form
    
    def form_valid(self, form):
        bus = form.save(commit=False)
        user = self.request.user
        bus.org = user.profile.org
        bus.save()
        return redirect('central_admin:bus_list')
    
    
class BusUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = Bus
    form_class = BusForm
    template_name = 'central_admin/bus_update.html'
    success_url = reverse_lazy('central_admin:bus_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['route'].queryset = Route.objects.filter(org=self.request.user.profile.org)
        form.fields['time_slot'].queryset = TimeSlot.objects.filter(org=self.request.user.profile.org)
        return form

    def form_valid(self, form):
        return super().form_valid(form)


class BusDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Bus
    template_name = 'central_admin/bus_confirm_delete.html'
    success_url = reverse_lazy('central_admin:bus_list')
    
    
class PeopleListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = UserProfile
    template_name = 'central_admin/people_list.html'
    context_object_name = 'people'
    
    def get_queryset(self):
        queryset = UserProfile.objects.filter(org=self.request.user.profile.org)
        return queryset
    

class PeopleCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
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
            
            # Generate password reset link
            token_generator = PasswordResetTokenGenerator()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)

            reset_link = self.request.build_absolute_uri(
                reverse('core:confirm_password_reset', kwargs={'uidb64': uid, 'token': token})
            )
            
            subject = "Welcome to SFS Busnest"
            message = (
            f"Hello,\n\n"
            f"Welcome to our BusNest! You have been added to the system by "
            f"{self.request.user.profile.first_name} {self.request.user.profile.last_name}. "
            f"Please set your password using the link below.\n\n"
            f"{reset_link}\n\n"
            f"Best regards,\nSFSBusNest Team"
            )
            recipient_list = [f"{user.email}"]
            
            send_email_task.delay(subject, message, recipient_list)
            
            return redirect(self.success_url)
        except Exception as e:
            print(self.request, f"An error occurred: {str(e)}")
            return self.form_invalid(form)
        
        
class PeopleUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = UserProfile
    form_class = PeopleUpdateForm
    template_name = 'central_admin/people_update.html'
    success_url = reverse_lazy('central_admin:people_list')

    def form_valid(self, form):
        return super().form_valid(form)
    

class PeopleDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = UserProfile
    template_name = 'central_admin/people_confirm_delete.html'
    success_url = reverse_lazy('central_admin:people_list')


class RouteListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = Route
    template_name = 'central_admin/route_list.html'
    context_object_name = 'routes'
    
    def get_queryset(self):
        queryset = Route.objects.filter(org=self.request.user.profile.org)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stops"] = Stop.objects.filter(org=self.request.user.profile.org)
        return context
    

class RouteFileUploadView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/route_file_upload.html'
    model = RouteFile
    fields = ['name', 'file']
    
    def form_valid(self, form):
        route_file = form.save(commit=False)
        user = self.request.user
        route_file.org = user.profile.org
        route_file.save()
        process_uploaded_csv.delay(route_file.file.name, user.profile.org.id, route_file.name)
        return redirect('central_admin:route_list')
        

class RouteCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/route_create.html'
    model = Route
    form_class = RouteForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['stops'].queryset = Stop.objects.filter(org=self.request.user.profile.org)
        return form
    
    def form_valid(self, form):
        route = form.save(commit=False)
        user = self.request.user
        route.org = user.profile.org
        route.save()
        form.save_m2m()
        return redirect('central_admin:route_list')
    
    
class RouteUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = Route
    form_class = RouteForm
    template_name = 'central_admin/route_update.html'
    success_url = reverse_lazy('central_admin:route_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['stops'].queryset = Stop.objects.filter(org=self.request.user.profile.org)
        return form

    def form_valid(self, form):
        return super().form_valid(form)
    
    
class RouteDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Route
    template_name = 'central_admin/route_confirm_delete.html'
    success_url = reverse_lazy('central_admin:route_list')
    

class StopCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/stop_create.html'
    model = Stop
    form_class = StopForm
    
    def form_valid(self, form):
        stop = form.save(commit=False)
        user = self.request.user
        stop.org = user.profile.org
        stop.save()
        return redirect('central_admin:route_list')
    

class StopDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Stop
    template_name = 'central_admin/stop_confirm_delete.html'
    success_url = reverse_lazy('central_admin:route_list')


class RegistraionListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = Registration
    template_name = 'central_admin/registration_list.html'
    context_object_name = 'registrations'
    
    def get_queryset(self):
        queryset = Registration.objects.filter(org=self.request.user.profile.org)
        return queryset
    
    
class RegistrationCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/registration_create.html'
    model = Registration
    form_class = RegistrationForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['stops'].queryset = Stop.objects.filter(org=self.request.user.profile.org)
        return form
    
    def form_valid(self, form):
        registration = form.save(commit=False)
        user = self.request.user
        registration.org = user.profile.org
        registration.save()
        form.save_m2m()
        return redirect('central_admin:registration_list')
    
    
class RegistrationDetailView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DetailView):
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


class RegistrationUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = Registration
    form_class = RegistrationForm
    template_name = 'central_admin/registration_update.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['stops'].queryset = Stop.objects.filter(org=self.request.user.profile.org)
        return form

    def form_valid(self, form):
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faq_form'] = FAQForm
        context['protocol'] = self.request.scheme
        context['domain'] = self.request.get_host()
        return context
    
    def get_success_url(self):
        return reverse('central_admin:registration_detail', kwargs={'slug': self.kwargs['slug']})
    

class RegistrationDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Registration
    template_name = 'central_admin/registration_confirm_delete.html'
    success_url = reverse_lazy('central_admin:registration_list')
    
    
class TicketListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = Ticket
    template_name = 'central_admin/ticket_list.html'
    context_object_name = 'tickets'
    
    def get_queryset(self):
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)
        
        # Base queryset filtered by registration and institution
        queryset = Ticket.objects.filter(org=self.request.user.profile.org, registration=self.registration).order_by('-created_at')
        
        # Apply filters based on GET parameters
        institution = self.request.GET.get('institution')
        pickup_points = self.request.GET.getlist('pickup_point')
        drop_points = self.request.GET.getlist('drop_point')
        time_slot = self.request.GET.get('time_slot')
        student_group = self.request.GET.get('student_group')
        filters = False  # Default no filters applied
        
        self.search_term = self.request.GET.get('search', '')
        
        if self.search_term:
            queryset = Ticket.objects.filter(
                Q(student_name__icontains=self.search_term) |
                Q(student_email__icontains=self.search_term) |
                Q(student_id__icontains=self.search_term) |
                Q(contact_no__icontains=self.search_term) |
                Q(alternative_contact_no__icontains=self.search_term)
            )

        # Apply filters based on GET parameters and update the filters flag
        if institution:
            queryset = queryset.filter(institution_id=institution)
            filters = True
        if pickup_points and not pickup_points == ['']:
            queryset = queryset.filter(pickup_point_id__in=pickup_points)
            filters = True
        if drop_points and not drop_points == ['']:
            queryset = queryset.filter(drop_point_id__in=drop_points)
            filters = True
        if time_slot:
            queryset = queryset.filter(time_slot_id=time_slot)
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
        context['pickup_points'] = Stop.objects.filter(org=self.registration.org)
        context['drop_points'] = Stop.objects.filter(org=self.registration.org)
        context['time_slots'] = TimeSlot.objects.filter(org=self.registration.org)
        context['institutions'] = Institution.objects.filter(org=self.registration.org)
        context['search_term'] = self.search_term

        return context
    

class FAQCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
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
    
    
class FAQDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = FAQ
    template_name = 'central_admin/registration_confirm_delete.html'
    slug_url_kwarg = 'faq_slug'
    
    def get_success_url(self):
        return reverse('central_admin:registration_update', kwargs={'slug': self.kwargs['registration_slug']})
    

class TimeSlotListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = TimeSlot
    template_name = 'central_admin/time_slot_list.html'
    context_object_name = 'time_slots'
    
    def get_queryset(self):
        queryset = TimeSlot.objects.filter(org=self.request.user.profile.org)
        return queryset


class TimeSlotCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    model = TimeSlot
    template_name = 'central_admin/time_slot_create.html'
    form_class = TimeSlotForm
    
    def form_valid(self, form):
        time_slot = form.save(commit=False)
        time_slot.org = self.request.user.profile.org
        time_slot.save()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('central_admin:time_slot_list')
    

class TimeSlotUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = TimeSlot
    template_name = 'central_admin/time_slot_update.html'
    form_class = TimeSlotForm
    slug_url_kwarg = 'time_slot_slug'
    
    def get_success_url(self):
        return reverse('central_admin:time_slot_list')

    
class MoreMenuView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    template_name = 'central_admin/more_menu.html'
