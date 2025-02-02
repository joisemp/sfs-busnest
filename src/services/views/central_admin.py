import threading
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View, FormView
from services.models import Institution, Bus, Stop, Route, RouteFile, Registration, Ticket, FAQ, Schedule, BusRequest, BusRecord, BusFile, OrganisationActivity
from core.models import UserProfile
from django.db import transaction, IntegrityError
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models import Q, Count, F
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from urllib.parse import urlencode

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin

from services.forms.central_admin import PeopleCreateForm, PeopleUpdateForm, InstitutionForm, BusForm, RouteForm, StopForm, RegistrationForm, FAQForm, ScheduleForm, BusRecordCreateForm, BusRecordUpdateForm, BusSearchForm

from services.tasks import process_uploaded_route_excel, send_email_task, export_tickets_to_excel, process_uploaded_bus_excel


User = get_user_model()


class DashboardView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    template_name = 'central_admin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['org'] = self.request.user.profile.org
        context['active_registrations'] = Registration.objects.filter(org=self.request.user.profile.org).count()
        context['buses_available'] = Bus.objects.filter(org=self.request.user.profile.org).count()
        context['institution_count'] = Institution.objects.filter(org=self.request.user.profile.org).count()
        context['recent_activities'] = OrganisationActivity.objects.filter(org=self.request.user.profile.org).count()
        return context


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

    def form_valid(self, form):
        return super().form_valid(form)


class BusFileUploadView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/bus_file_upload.html'
    model = BusFile
    fields = ['name', 'file']
    
    def form_valid(self, form):
        bus_file = form.save(commit=False)
        user = self.request.user
        bus_file.org = user.profile.org
        bus_file.user = user
        bus_file.save()
        process_uploaded_bus_excel.delay(bus_file.file.name, bus_file.org.id)
        return redirect(reverse('central_admin:bus_list'))


class BusDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Bus
    template_name = 'central_admin/bus_confirm_delete.html'
    success_url = reverse_lazy('central_admin:bus_list')
    

class BusRecordListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = BusRecord
    template_name = 'central_admin/bus_record_list.html'
    context_object_name = 'bus_records'
    
    def get_queryset(self):
        self.noneRecords = self.request.GET.get('noneRecords')
        if self.noneRecords == 'True':
            queryset = BusRecord.objects.filter(org=self.request.user.profile.org, bus=None, registration__slug=self.kwargs["registration_slug"]).order_by('label')
        else:
            queryset = BusRecord.objects.filter(org=self.request.user.profile.org, registration__slug=self.kwargs["registration_slug"]).order_by('label')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        if BusRecord.objects.filter(org=self.request.user.profile.org, bus=None, registration__slug=self.kwargs["registration_slug"]):
            context["blank_records"] = True
        if self.noneRecords:
            context['reset_filter'] = True
        return context
    

class BusRecordCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    model = BusRecord
    template_name = 'central_admin/bus_record_create.html'
    form_class = BusRecordCreateForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org = self.request.user.profile.org if hasattr(self.request.user, 'profile') else None
        
        if user_org:
            form.fields['bus'].queryset = Bus.objects.filter(org=user_org)
            form.fields['route'].queryset = Route.objects.filter(org=user_org)
        else:
            # Optionally raise an exception or show a custom error if the profile/org is missing
            form.fields['bus'].queryset = Bus.objects.none()
            form.fields['route'].queryset = Route.objects.none()
        
        return form

    @transaction.atomic
    def form_valid(self, form):
        try:
            # Get the registration based on slug
            registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
            
            # Check if a BusRecord already exists
            if BusRecord.objects.filter(bus=form.cleaned_data['bus'], registration=registration, schedule=form.cleaned_data['schedule']).exists():
                form.add_error(None, "A record with this bus, schedule and registration already exists.")
                return self.form_invalid(form)

            # Save the BusRecord
            bus_record = form.save(commit=False)
            bus_record.org = self.request.user.profile.org
            bus_record.registration = registration
            bus_record.save()

        except ObjectDoesNotExist:
            form.add_error(None, "The specified registration does not exist.")
            return self.form_invalid(form)

        except IntegrityError:
            form.add_error(None, "A unique constraint was violated while saving the record.")
            return self.form_invalid(form)

        # Redirect to the success URL
        messages.success(self.request, "Bus Record created successfully!")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('central_admin:bus_record_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class BusRecordUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = BusRecord
    template_name = 'central_admin/bus_record_update.html'
    form_class = BusRecordUpdateForm
    slug_field = 'slug'
    slug_url_kwarg = 'bus_record_slug'

    @transaction.atomic
    def form_valid(self, form):
        try:
            # Fetch registration
            registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
            
            # Get the new bus from the form
            new_bus = form.cleaned_data.get('bus')
            
            new_schedule = form.cleaned_data.get('schedule')
            
            # Check for existing BusRecord with the same bus and registration
            existing_record = BusRecord.objects.filter(bus=new_bus, schedule=new_schedule, registration=registration).exclude(pk=self.object.pk).first()
            if existing_record:
                existing_record.bus = None
                existing_record.save()

            # Save the updated record
            bus_record = form.save(commit=False)
            bus_record.registration = registration
            bus_record.save()

            # Success message
            messages.success(self.request, "Bus Record updated successfully!")
            return redirect(self.get_success_url())

        except ObjectDoesNotExist:
            form.add_error(None, "The specified registration does not exist.")
            return self.form_invalid(form)

        except IntegrityError:
            form.add_error(None, "A unique constraint was violated while updating the record.")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('central_admin:bus_record_list', kwargs={'registration_slug': self.kwargs['registration_slug']})

    
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
        context["stops"] = Stop.objects.filter(org=self.request.user.profile.org).order_by('-id')[:15]
        context["registration"] = Registration.objects.get(slug=self.kwargs['registration_slug'])
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
        registration = Registration.objects.get(slug=self.kwargs['registration_slug'])
        thread = threading.Thread(target=process_uploaded_route_excel(route_file.file.name, user.profile.org.id, registration.id))
        thread.start()
        # process_uploaded_route_excel.delay(route_file.file.name, user.profile.org.id, registration.id)
        return redirect(reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']}))
        

class RouteCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/route_create.html'
    model = Route
    form_class = RouteForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['stops'].queryset = Stop.objects.filter(org=self.request.user.profile.org)
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def form_valid(self, form):
        route = form.save(commit=False)
        user = self.request.user
        route.org = user.profile.org
        route.save()
        form.save_m2m()
        return redirect(reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']}))
    
    
class RouteUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = Route
    form_class = RouteForm
    template_name = 'central_admin/route_update.html'
    slug_field = 'slug'
    slug_url_kwarg = 'route_slug'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['stops'].queryset = Stop.objects.filter(org=self.request.user.profile.org)
        return form

    def form_valid(self, form):
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    
    
class RouteDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Route
    template_name = 'central_admin/route_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'route_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return redirect(reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']}))
    

class StopCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    template_name = 'central_admin/stop_create.html'
    model = Stop
    form_class = StopForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def form_valid(self, form):
        stop = form.save(commit=False)
        user = self.request.user
        stop.org = user.profile.org
        stop.save()
        return redirect('central_admin:route_list')
    

class StopDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Stop
    template_name = 'central_admin/stop_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'stop_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return redirect(reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']}))


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
    slug_url_kwarg = 'registration_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tickets = self.object.tickets.filter(org=self.request.user.profile.org).order_by('-created_at')[:10]
        context['recent_tickets'] = tickets
        return context


class RegistrationUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = Registration
    form_class = RegistrationForm
    template_name = 'central_admin/registration_update.html'
    slug_field = 'slug'
    slug_url_kwarg = 'registration_slug'

    def form_valid(self, form):
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faq_form'] = FAQForm
        context['protocol'] = self.request.scheme
        context['domain'] = self.request.get_host()
        return context
    
    def get_success_url(self):
        return reverse('central_admin:registration_detail', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class RegistrationDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = Registration
    template_name = 'central_admin/registration_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'registration_slug'
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
        schedule = self.request.GET.get('schedule')
        pickup_buses = self.request.GET.getlist('pickup_bus')
        drop_buses = self.request.GET.getlist('drop_bus')
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
        if schedule:
            queryset = queryset.filter(schedule_id=schedule)
            filters = True
        if pickup_buses and not pickup_buses == ['']:
            queryset = queryset.filter(pickup_bus_record_id__in=pickup_buses)
            filters = True
        if drop_buses and not drop_buses == ['']:
            queryset = queryset.filter(drop_bus_record_id__in=drop_buses)
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
        context['pickup_points'] = Stop.objects.filter(org=self.registration.org, registration=self.registration)
        context['drop_points'] = Stop.objects.filter(org=self.registration.org, registration=self.registration)
        context['schedules'] = Schedule.objects.filter(org=self.registration.org, registration=self.registration)
        context['institutions'] = Institution.objects.filter(org=self.registration.org)
        context['bus_records'] = BusRecord.objects.filter(org=self.registration.org, registration=self.registration).order_by("label")
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
    

class ScheduleListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = Schedule
    template_name = 'central_admin/schedule_list.html'
    context_object_name = 'schedules'
    
    def get_queryset(self):
        self.registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        queryset = Schedule.objects.filter(org=self.request.user.profile.org, registration=self.registration)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = self.registration
        return context


class ScheduleCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    model = Schedule
    template_name = 'central_admin/schedule_create.html'
    form_class = ScheduleForm
    
    def form_valid(self, form):
        schedule = form.save(commit=False)
        schedule.org = self.request.user.profile.org
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        schedule.registration = registration
        schedule.save()
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return reverse('central_admin:schedule_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class ScheduleUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = Schedule
    template_name = 'central_admin/schedule_update.html'
    form_class = ScheduleForm
    slug_url_kwarg = 'schedule_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
            
    def get_success_url(self):
        return reverse('central_admin:schedule_list', kwargs={'registration_slug': self.kwargs['registration_slug']})

    
class MoreMenuView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    template_name = 'central_admin/more_menu.html'


# class TicketExportView(View):
#     def post(self, request, *args, **kwargs):
#         registration_slug = self.kwargs.get('registration_slug')
#         registration = get_object_or_404(Registration, slug=registration_slug)
        
#         search_term = request.GET.get('search', '')
#         institution = request.GET.get('institution')
#         pickup_points = request.GET.getlist('pickup_point')
#         drop_points = request.GET.getlist('drop_point')
#         schedule = request.GET.get('schedule')
#         pickup_buses = self.request.GET.getlist('pickup_bus')
#         drop_buses = self.request.GET.getlist('drop_bus')
        
#         # Base queryset filtered by registration and institution
#         queryset = Ticket.objects.filter(org=request.user.profile.org, registration=registration).order_by('-created_at')
        
#         # Apply search term filters
#         if search_term:
#             queryset = queryset.filter(
#                 Q(student_name__icontains=search_term) |
#                 Q(student_email__icontains=search_term) |
#                 Q(student_id__icontains=search_term) |
#                 Q(contact_no__icontains=search_term) |
#                 Q(alternative_contact_no__icontains=search_term)
#             )
        
#         # Apply other filters
#         if institution:
#             queryset = queryset.filter(institution_id=institution)
#         if pickup_points and pickup_points != ['']:
#             queryset = queryset.filter(pickup_point_id__in=pickup_points)
#         if drop_points and drop_points != ['']:
#             queryset = queryset.filter(drop_point_id__in=drop_points)
#         if schedule:
#             queryset = queryset.filter(schedule_id=schedule)
#         if pickup_buses and not pickup_buses == ['']:
#             queryset = queryset.filter(pickup_bus_record_id__in=pickup_buses)
#         if drop_buses and not drop_buses == ['']:
#             queryset = queryset.filter(drop_bus_record_id__in=drop_buses)
        
#         # Send the filtered queryset to the Celery task for export
#         # export_tickets_to_excel.apply_async(
#         #     args=[request.user.id, registration_slug, search_term, {
#         #         'institution': institution,
#         #         'pickup_points': pickup_points,
#         #         'drop_points': drop_points,
#         #         'schedule': schedule,
#         #         'pickup_buses': pickup_buses,
#         #         'drop_buses': drop_buses,
#         #     }]
#         # )
        
        
#         thread = threading.Thread(target=export_tickets_to_excel, args=[
#             request.user.id, registration_slug, search_term, {
#                 'institution': institution,
#                 'pickup_points': pickup_points,
#                 'drop_points': drop_points,
#                 'schedule': schedule,
#                 'pickup_buses': pickup_buses,
#                 'drop_buses': drop_buses,
#             }
#         ])
#         thread.start()
        
#         return JsonResponse({"message": "Export request received. You will be notified once the export is ready."})
    

class TicketExportView(View):
    def get(self, request, *args, **kwargs):
        registration_slug = self.kwargs.get('registration_slug')
        search_term = request.GET.get('search', '')
        institution = request.GET.get('institution')
        pickup_points = request.GET.getlist('pickup_point')
        drop_points = request.GET.getlist('drop_point')
        schedule = request.GET.get('schedule')
        pickup_buses = request.GET.getlist('pickup_bus')
        drop_buses = request.GET.getlist('drop_bus')

        filters = {
            'institution': institution,
            'pickup_points': pickup_points,
            'drop_points': drop_points,
            'schedule': schedule,
            'pickup_buses': pickup_buses,
            'drop_buses': drop_buses,
        }

        return export_tickets_to_excel(request.user.id, registration_slug, search_term, filters)
    

class BusRequestListView(ListView):
    model = BusRequest
    template_name = 'central_admin/bus_request_list.html'
    context_object_name = 'bus_requests'
    
    def get_queryset(self):
        queryset = BusRequest.objects.filter(org=self.request.user.profile.org)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context


class BusSearchFormView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, FormView):
    template_name = 'central_admin/bus_search_form.html'
    form_class = BusSearchForm

    def get_registration(self):
        """Fetch registration using the code from the URL."""
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        registration = self.get_registration()
        form.fields['stop'].queryset = registration.stops.all()
        return form

    def form_valid(self, form):
        stop = form.cleaned_data['stop']
        schedule = form.cleaned_data['schedule']
        self.request.session['stop_id'] = stop.id
        self.request.session['schedule_id'] = schedule.id
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        
        change_type = self.request.GET.get('changeType')  
        
        if change_type == 'pickup':
            context['change_type'] = 'pickup'
        elif change_type == 'drop':
            context['change_type'] = 'drop'
        
        return context

    def get_success_url(self):
        registration_code = self.get_registration().code
        change_type = self.request.GET.get('changeType') 
        ticket_id = self.kwargs.get('ticket_id')
        query_params = {'changeType': change_type}
        search_result_base_url = reverse('central_admin:bus_search_results', kwargs={'ticket_id': ticket_id, 'registration_code': registration_code})
        return f"{search_result_base_url}?{urlencode(query_params)}"


class BusSearchResultsView(ListView):
    template_name = 'central_admin/bus_search_results.html'
    context_object_name = 'bus_records'

    def get_queryset(self):
        # Retrieve the registration based on the registration code
        registration_code = self.kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)

        # Get stop and schedule from session
        self.stop_id = self.request.session.get('stop_id')
        self.schedule_id = self.request.session.get('schedule_id')
        self.change_type = self.request.GET.get('changeType')

        # Return empty queryset if required data is missing
        if not (self.stop_id and self.schedule_id):
            return BusRecord.objects.none()

        # Initialize buses with an empty queryset
        buses = BusRecord.objects.none()

        # Filter logic based on changeType
        if self.change_type == 'pickup':
            buses = BusRecord.objects.filter(
                org=registration.org,
                registration=registration,
                schedule_id=self.schedule_id,
                pickup_booking_count__lt=F('bus__capacity'),  # Pickup count must be less than capacity
                route__stops__id=self.stop_id,  # Stop must be in the route
            ).annotate(available_seats=F('bus__capacity') - F('pickup_booking_count'))
        elif self.change_type == 'drop':
            buses = BusRecord.objects.filter(
                org=registration.org,
                registration=registration,
                schedule_id=self.schedule_id,
                drop_booking_count__lt=F('bus__capacity'),  # Drop count must be less than capacity
                route__stops__id=self.stop_id,  # Stop must be in the route
            ).annotate(available_seats=F('bus__capacity') - F('drop_booking_count'))

        return buses.distinct()

    def get_context_data(self, **kwargs):
        """Include additional context like the registration."""
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        context['stop'] = get_object_or_404(Stop, id=self.stop_id)
        context['schedule'] = get_object_or_404(Schedule, id=self.schedule_id)
        context['ticket'] = get_object_or_404(Ticket, ticket_id=self.kwargs.get('ticket_id'))
        context['change_type'] = self.change_type
        return context
    

class UpdateBusInfoView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    @transaction.atomic
    def get(self, request, registration_code, ticket_id, bus_record_slug):
        registration = get_object_or_404(Registration, code=registration_code)
        ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
        
        change_type = self.request.GET.get('changeType')
        
        stop_id = self.request.session.get('stop_id')
        
        stop = get_object_or_404(Stop, id=stop_id)
        
        if change_type == 'pickup':
            new_bus_record = get_object_or_404(BusRecord, slug=bus_record_slug)
            current_pickup_bus_record = ticket.pickup_bus_record
            
            current_pickup_bus_record.pickup_booking_count -= 1
            new_bus_record.pickup_booking_count += 1
            new_bus_record.save()
            current_pickup_bus_record.save()
            
            ticket.pickup_bus_record = new_bus_record
            ticket.pickup_point = stop
            ticket.save()
            
        if change_type == 'drop':
            new_bus_record = get_object_or_404(BusRecord, slug=bus_record_slug)
            current_drop_bus_record = ticket.drop_bus_record
            
            current_drop_bus_record.drop_booking_count -= 1
            new_bus_record.drop_booking_count += 1
            new_bus_record.save()
            current_drop_bus_record.save()
            
            ticket.drop_bus_record = new_bus_record
            ticket.drop_point = stop
            ticket.save()
        
        return redirect(
            reverse('central_admin:ticket_list', 
                    kwargs={'registration_slug': registration.slug}
                )
            )
    
