import threading
from urllib.parse import urlencode
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, DeleteView, UpdateView, FormView, View
from django.urls import reverse, reverse_lazy
from services.forms.central_admin import BusRequestCommentForm
from services.forms.students import StopSelectForm
from services.models import Bus, BusRecord, BusRequest, BusRequestComment, Registration, Receipt, ScheduleGroup, Stop, StudentGroup, Ticket, Schedule, ReceiptFile, Trip
from services.forms.institution_admin import ReceiptForm, StudentGroupForm, TicketForm, BusSearchForm, BulkStudentGroupUpdateForm
from config.mixins.access_mixin import InsitutionAdminOnlyAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.template.loader import render_to_string
from services.tasks import process_uploaded_receipt_data_excel, export_tickets_to_excel, bulk_update_student_groups_task
from services.utils.utils import get_filtered_bus_records
import openpyxl
from django.contrib import messages

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
    paginate_by = 15
    
    def get_queryset(self):
        # Get registration based on slug
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)
        
        # Base queryset filtered by registration and institution
        queryset = Ticket.objects.filter(registration=self.registration, institution=self.request.user.profile.institution).order_by('-created_at')
        
        # Apply filters based on GET parameters
        pickup_points = self.request.GET.getlist('pickup_point')
        drop_points = self.request.GET.getlist('drop_point')
        schedule = self.request.GET.get('schedule')
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
        if pickup_points and not pickup_points == ['']:
            queryset = queryset.filter(pickup_point_id__in=pickup_points)
            filters = True
        if drop_points and not drop_points == ['']:
            queryset = queryset.filter(drop_point_id__in=drop_points)
            filters = True
        if schedule:
            queryset = queryset.filter(schedule_id=schedule)
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
        context['schedules'] = Schedule.objects.filter(
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


class TicketDeleteView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, DeleteView):
    model = Ticket
    template_name = 'institution_admin/ticket_confirm_delete.html'
    slug_url_kwarg = 'ticket_slug'
    
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
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)
        queryset = Receipt.objects.filter(
            org=self.request.user.profile.org,
            institution=self.request.user.profile.institution,
            registration=self.registration
        ).order_by('-created_at')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.registration  # Ensure registration is passed to the template
        return context
    

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
        process_uploaded_receipt_data_excel.delay(
            self.request.user.id,
            receipt_data_file.file.name,
            user.profile.org.id,
            user.profile.institution.id,
            receipt_data_file.registration.id
        )
        return redirect(
            reverse(
                'institution_admin:receipt_list',
                kwargs={'registration_slug': receipt_data_file.registration.slug}
            )
        )
    
    
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
        return redirect(
            reverse(
                'institution_admin:receipt_list',
                kwargs={'registration_slug': receipt.registration.slug}
            )
        )
    

class ReceiptDeleteView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, DeleteView):
    model = Receipt
    template_name = 'institution_admin/receipt_confirm_delete.html'
    slug_url_kwarg = 'receipt_slug'

    def get_success_url(self):
        return reverse(
            'institution_admin:receipt_list',
            kwargs={'registration_slug': self.object.registration.slug}
        )
    
    
class StudentGroupListView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, ListView):
    model = StudentGroup
    template_name = 'institution_admin/student_group_list.html'
    context_object_name = 'student_groups'  
    
    def get_queryset(self):
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)
        queryset = StudentGroup.objects.filter(
            org=self.request.user.profile.org,
            institution=self.request.user.profile.institution
        ).order_by('name')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.registration  # Ensure registration is passed to the template
        return context
    
    
class StudentGroupCreateView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, CreateView):
    template_name = 'institution_admin/student_group_create.html'
    model = StudentGroup
    form_class = StudentGroupForm

    def form_valid(self, form):
        student_group = form.save(commit=False)
        user = self.request.user
        student_group.org = user.profile.org
        student_group.institution = user.profile.institution
        student_group.save()
        return redirect(
            reverse(
                'institution_admin:student_group_list',
                kwargs={'registration_slug': self.kwargs['registration_slug']}
            )
        )


class StudentGroupUpdateView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, UpdateView):
    model = StudentGroup
    form_class = StudentGroupForm
    template_name = 'institution_admin/student_group_update.html'
    slug_url_kwarg = 'student_group_slug'

    def get_success_url(self):
        return reverse(
            'institution_admin:student_group_list',
            kwargs={'registration_slug': self.kwargs['registration_slug']}
        )

    def form_valid(self, form):
        return super().form_valid(form)
    
    
class StudentGroupDeleteView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, DeleteView):
    model = StudentGroup
    template_name = 'institution_admin/student_group_confirm_delete.html'
    slug_url_kwarg = 'student_group_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, slug=self.kwargs['registration_slug'])
        return context

    def get_success_url(self):
        return reverse(
            'institution_admin:student_group_list',
            kwargs={'registration_slug': self.kwargs['registration_slug']}
        )
    
    
class BusSearchFormView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, FormView):
    template_name = 'institution_admin/bus_search_form.html'
    form_class = BusSearchForm

    def get_registration(self):
        """Fetch registration using the code from the URL."""
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        registration = self.get_registration()
        form.fields['pickup_point'].queryset = registration.stops.all()
        form.fields['drop_point'].queryset = registration.stops.all()
        return form

    def form_valid(self, form):
        pickup_point = form.cleaned_data['pickup_point']
        drop_point = form.cleaned_data['drop_point']
        schedule = form.cleaned_data['schedule']

        # Store search criteria in the session for passing to results view
        self.request.session['pickup_point'] = pickup_point.id
        self.request.session['drop_point'] = drop_point.id
        self.request.session['schedule'] = schedule.id

        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context

    def get_success_url(self):
        registration_code = self.get_registration().code
        ticket_id = self.kwargs.get('ticket_id')
        return reverse('institution_admin:bus_search_results', kwargs={'ticket_id': ticket_id, 'registration_code': registration_code})
    

class BusSearchResultsView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, ListView):
    template_name = 'institution_admin/bus_search_results.html'
    context_object_name = 'buses'

    def get_queryset(self):
        registration_code = self.kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)

        self.pickup_point_id = self.request.session.get('pickup_point')
        self.drop_point_id = self.request.session.get('drop_point')
        self.schedule_id = self.request.session.get('schedule')

        if not (self.pickup_point_id and self.drop_point_id and self.schedule_id):
            return Bus.objects.none()
        
        buses = Bus.objects.filter(
            org=registration.org,
            schedule_id=self.schedule_id,
        ).filter(
            Q(route__stops__id=self.pickup_point_id) if self.pickup_point_id == self.drop_point_id else Q(route__stops__id__in=[self.pickup_point_id, self.drop_point_id])
        ).annotate(
            matching_stops=Count('route__stops', filter=Q(route__stops__id__in=[self.pickup_point_id, self.drop_point_id]))
        ).filter(
            matching_stops=1 if self.pickup_point_id == self.drop_point_id else 2
        ).distinct()

        # Subquery to fetch available seats from BusCapacity
        # bus_capacity_subquery = BusCapacity.objects.filter(
        #     bus=OuterRef('pk'),
        #     registration=registration
        # ).values('available_seats')

        # Annotate buses with available seats or fallback to total capacity
        # buses = buses.annotate(
        #     available_seats=Coalesce(Subquery(bus_capacity_subquery), F('capacity'))
        # )

        return buses

    def get_context_data(self, **kwargs):
        """Include additional context like the registration."""
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        context['ticket'] = get_object_or_404(Ticket, ticket_id=self.kwargs.get('ticket_id'))
        context['pickup_point'] = get_object_or_404(Stop, id=self.pickup_point_id)
        context['drop_point'] = get_object_or_404(Stop, id=self.drop_point_id)
        context['schedule'] = get_object_or_404(Schedule, id=self.schedule_id)
        return context
    

class TicketExportView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, View):
    def post(self, request, *args, **kwargs):
        registration_slug = self.kwargs.get('registration_slug')
        search_term = request.GET.get('search', '')
        # Always filter by the current user's institution for institution admin
        filters = {
            'institution': request.user.profile.institution.id,
            'pickup_points': request.GET.getlist('pickup_point'),
            'drop_points': request.GET.getlist('drop_point'),
            'schedule': request.GET.get('schedule'),
            'pickup_buses': request.GET.getlist('pickup_bus'),
            'drop_buses': request.GET.getlist('drop_bus'),
            'student_group': request.GET.get('student_group'),
        }

        # Trigger the Celery task
        export_tickets_to_excel.apply_async(
            args=[request.user.id, registration_slug, search_term, filters]
        )

        return JsonResponse({"message": "Export request received. You will be notified once the export is ready."})
    
    
class StopSelectFormView(FormView):
    template_name = 'students/search_form.html'
    form_class = StopSelectForm

    def get_registration(self):
        """Fetch registration using the code from the URL."""
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        registration = self.get_registration()
        form.fields['stop'].queryset = registration.stops.all().order_by('name')
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        return context

    def form_valid(self, form):
        stop = form.cleaned_data['stop']
        self.request.session['stop_id'] = stop.id
        return super().form_valid(form)

    def get_success_url(self):
        registration_code = self.get_registration().code
        query_string = self.request.GET.get('type', '')
        return reverse('institution_admin:schedule_group_select', kwargs={'registration_code': registration_code, 'ticket_id': self.kwargs.get('ticket_id')}) + f"?type={query_string}"
    

class SelectScheduleGroupView(View):
    template_name = 'institution_admin/select_schedule_group.html'

    def get(self, request, registration_code, ticket_id):
        registration = get_object_or_404(Registration, code=registration_code)
        schedules = Schedule.objects.filter(org=registration.org, registration=registration)
        query_string = self.request.GET.get('type', '')
        type = query_string if query_string else 'pickup and drop'
        return render(request, self.template_name, {'schedules': schedules, 'type': type})

    def post(self, request, registration_code, ticket_id):
        selected_id = request.POST.get("schedule_group")

        if not selected_id:
            registration = get_object_or_404(Registration, code=registration_code)
            schedules = Schedule.objects.filter(org=registration.org, registration=registration)
            query_string = self.request.GET.get('type', '')
            type = query_string if query_string else 'pickup and drop'
            return render(
                request,
                self.template_name,
                {
                    'schedules': schedules,
                    'type': type,
                    'error_message': "Please select a schedule.",
                }
            )

        selected_schedule = Schedule.objects.get(id=selected_id)
        
        # Process the selection
        selection_details = {
            "selected_schedule": selected_schedule,
        }
        
        self.request.session['schedule_id'] = selection_details['selected_schedule'].id
        query_string = self.request.GET.get('type', '')
        return HttpResponseRedirect(reverse('institution_admin:bus_search_results', kwargs={'registration_code': registration_code, 'ticket_id': self.kwargs.get('ticket_id')})+ f"?type={query_string}")
    
    
class BusSearchResultsView(ListView):
    template_name = 'institution_admin/search_results.html'
    context_object_name = 'buses'

    def get_queryset(self):
        # Get pickup point, drop point, and schedule from session
        stop_id = self.request.session.get('stop_id')
        schedule_id = self.request.session.get('schedule_id')
        query_string = self.request.GET.get('type', '')

        schedule = Schedule.objects.get(id=int(schedule_id))
        
        if query_string != '':
            schedule_ids = [schedule.id]
        else:
            raise Http404("Invalid query string")
        
        buses = get_filtered_bus_records(schedule_ids, int(stop_id))
        return buses
    
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        if not self.object_list:
            registration_code = self.kwargs.get('registration_code')
            return HttpResponseRedirect(reverse('students:bus_not_found', kwargs={'registration_code': registration_code}))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Include additional context like the registration."""
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        context['ticket'] = get_object_or_404(Ticket, ticket_id=self.kwargs.get('ticket_id'))
        context['change_type'] = self.request.GET.get('type', '')
        context['stop'] = Stop.objects.get(id=self.request.session.get('stop_id'))
        context['schedule'] = Schedule.objects.get(id=self.request.session.get('schedule_id'))
        return context


class UpdateBusInfoView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, View):
    @transaction.atomic
    def get(self, request, registration_code, ticket_id, bus_slug):
        registration = get_object_or_404(Registration, code=registration_code)
        ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
        bus_record = get_object_or_404(BusRecord, slug=bus_slug)
        
        stop_id = self.request.session.get('stop_id')
        schedule_id = self.request.session.get('schedule_id')
        
        pickup_point = get_object_or_404(Stop, id=stop_id)
        drop_point = get_object_or_404(Stop, id=stop_id)
        schedule = get_object_or_404(Schedule, id=schedule_id)
        
        change_type = self.request.GET.get('type')
        
        if change_type == 'pickup':
            new_trip = Trip.objects.get(registration=registration, record=bus_record, schedule=schedule)
            if ticket.pickup_bus_record and ticket.pickup_schedule:
                try:
                    existing_trip = Trip.objects.get(registration=registration, record=ticket.pickup_bus_record, schedule=ticket.pickup_schedule)
                    existing_trip.booking_count -= 1
                    existing_trip.save()
                except Trip.DoesNotExist:
                    pass
            ticket.pickup_bus_record = bus_record
            ticket.pickup_point = pickup_point
            ticket.pickup_schedule = schedule
            new_trip.booking_count += 1
            new_trip.save()
        
        elif change_type == 'drop':
            new_trip = Trip.objects.get(registration=registration, record=bus_record, schedule=schedule)
            if ticket.drop_bus_record and ticket.drop_schedule:
                try:
                    existing_trip = Trip.objects.get(registration=registration, record=ticket.drop_bus_record, schedule=ticket.drop_schedule)
                    existing_trip.booking_count -= 1
                    existing_trip.save()
                except Trip.DoesNotExist:
                    pass
            ticket.drop_bus_record = bus_record
            ticket.drop_point = drop_point
            ticket.drop_schedule = schedule
            new_trip.booking_count += 1
            new_trip.save()
        
        # Update the ticket type to 'two way' if both pickup and drop buses exist
        if ticket.pickup_bus_record and ticket.drop_bus_record:
            ticket.ticket_type = 'two_way'
        
        ticket.save()
        
        return redirect(
            reverse('institution_admin:ticket_list', 
                    kwargs={'registration_slug': registration.slug}
                )
            )


class BusRequestListView(ListView):
    model = BusRequest
    template_name = 'institution_admin/bus_request_list.html'
    context_object_name = 'bus_requests'
    paginate_by = 20
    
    def get_queryset(self):
        registration = get_object_or_404(Registration, slug=self.kwargs["registration_slug"])
        institution = self.request.user.profile.institution
        queryset = BusRequest.objects.filter(org=self.request.user.profile.org, institution=institution, registration=registration).order_by('-created_at')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context["registration"] = registration
        context["total_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration
        ).count()
        context["open_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration, 
            status='open'
        ).count()
        context["closed_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration, 
            status='closed'
        ).count()
        for request in context["bus_requests"]:
            request.has_ticket = Ticket.objects.filter(
                registration=registration, 
                recipt=request.receipt
            ).exists()
        return context

class BusRequestOpenListView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, ListView):
    model = BusRequest
    template_name = 'institution_admin/bus_request_list.html'
    context_object_name = 'bus_requests'
    paginate_by = 20
    
    def get_queryset(self):
        registration = get_object_or_404(Registration, slug=self.kwargs["registration_slug"])
        institution = self.request.user.profile.institution
        queryset = BusRequest.objects.filter(org=self.request.user.profile.org, institution=institution, registration=registration, status='open').order_by('-created_at')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context["registration"] = registration
        context["total_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration
        ).count()
        context["open_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration, 
            status='open'
        ).count()
        context["closed_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration, 
            status='closed'
        ).count()
        for request in context["bus_requests"]:
            request.has_ticket = Ticket.objects.filter(
                registration=registration, 
                recipt=request.receipt
            ).exists()
        return context

class BusRequestClosedListView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, ListView):
    model = BusRequest
    template_name = 'institution_admin/bus_request_list.html'
    context_object_name = 'bus_requests'
    paginate_by = 20
    
    def get_queryset(self):
        registration = get_object_or_404(Registration, slug=self.kwargs["registration_slug"])
        institution = self.request.user.profile.institution
        queryset = BusRequest.objects.filter(org=self.request.user.profile.org, institution=institution, registration=registration, status='closed').order_by('-created_at')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context["registration"] = registration
        context["total_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration
        ).count()
        context["open_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration, 
            status='open'
        ).count()
        context["closed_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            institution=self.request.user.profile.institution, 
            registration=registration, 
            status='closed'
        ).count()
        for request in context["bus_requests"]:
            request.has_ticket = Ticket.objects.filter(
                registration=registration, 
                recipt=request.receipt
            ).exists()
        return context

class BusRequestDeleteView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, DeleteView):
    model = BusRequest
    template_name = 'institution_admin/bus_request_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'bus_request_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.object.registration
        return context
    
    def get_success_url(self):
        return reverse('central_admin:bus_request_list', kwargs={'registration_slug': self.kwargs['registration_slug']})


class BusRequestStatusUpdateView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, View):
    def post(self, request, *args, **kwargs):
        bus_request = get_object_or_404(BusRequest, slug=self.kwargs['bus_request_slug'])
        new_status = 'open' if bus_request.status == 'closed' else 'closed'
        comment_text = request.POST.get('comment')
        bus_request.status = new_status
        bus_request.save()
        if comment_text:
            BusRequestComment.objects.create(
                bus_request=bus_request,
                comment=comment_text,
                created_by=request.user
            )
        modal_body_html = render_to_string('central_admin/bus_request_modal_body.html', {'bus_request': bus_request})
        response = HttpResponse(modal_body_html)
        response['HX-Trigger'] = 'reloadPage'
        return response

class BusRequestCommentView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, View):
    def post(self, request, *args, **kwargs):
        bus_request = get_object_or_404(BusRequest, slug=self.kwargs['bus_request_slug'])
        comment_form = BusRequestCommentForm(request.POST)
        if comment_form.is_valid():
            comment = BusRequestComment.objects.create(
                bus_request=bus_request,
                comment=comment_form.cleaned_data['comment'],
                created_by=request.user
            )
            comment_html = render_to_string('institution_admin/comment.html', {'comment': comment}).strip()
            return HttpResponse(comment_html)
        return HttpResponse('Invalid form submission', status=400)


class BulkStudentGroupUpdateView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, FormView):
    template_name = 'institution_admin/bulk_student_group_update_upload.html'
    form_class = BulkStudentGroupUpdateForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def form_valid(self, form):
        file = form.cleaned_data['file']
        wb = openpyxl.load_workbook(file, read_only=True)
        ws = wb.active
        preview_data = []
        errors = []
        institution = self.request.user.profile.institution

        # Validate header row
        header = [str(cell).strip().upper() if cell else "" for cell in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
        expected_header = ["STUDENT ID", "CLASS", "SECTION"]
        if header != expected_header:
            messages.error(self.request, "Excel file must have only these columns in order: STUDENT ID, CLASS, SECTION (no extra columns or data).")
            return render(self.request, self.template_name, {
                "form": form,
                "errors": errors,
            })

        # Collect all student_ids from the file for bulk query
        student_id_rows = []
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if row is None or len(row) != 3:
                errors.append(f"Row {idx}: Must have exactly 3 columns (STUDENT ID, CLASS, SECTION).")
                continue
            student_id, class_name, section = row
            if not student_id or not class_name or not section:
                errors.append(f"Row {idx}: Missing data")
                continue
            student_id_rows.append((idx, student_id, class_name, section))

        # Bulk fetch all tickets for student_ids
        student_ids = [str(student_id).strip() for _, student_id, _, _ in student_id_rows]
        tickets = Ticket.objects.filter(student_id__in=student_ids, institution=institution).select_related('student_group')
        ticket_map = {t.student_id: t for t in tickets}

        for idx, student_id, class_name, section in student_id_rows:
            group_name = f"{str(class_name).strip().upper()} - {str(section).strip().upper()}"
            ticket = ticket_map.get(str(student_id).strip())
            if ticket:
                current_group = ticket.student_group.name if ticket.student_group else ""
                preview_data.append({
                    "student_id": student_id,
                    "student_name": ticket.student_name,
                    "current_group": current_group,
                    "new_group": group_name,
                })
            else:
                errors.append(f"Row {idx}: Ticket not found for student_id {student_id}")

        self.request.session['bulk_update_preview'] = preview_data
        self.request.session['bulk_update_errors'] = errors
        return render(self.request, 'institution_admin/bulk_student_group_update_confirm.html', {
            "preview_data": preview_data,
            "errors": errors,
        })

    def dispatch(self, request, *args, **kwargs):
        registration_slug = self.kwargs.get('registration_slug')
        registration = get_object_or_404(Registration, slug=registration_slug)
        if registration.status:
            raise Http404("Bulk update is only allowed when registration is closed.")
        return super().dispatch(request, *args, **kwargs)

class BulkStudentGroupUpdateConfirmView(LoginRequiredMixin, InsitutionAdminOnlyAccessMixin, View):
    def post(self, request, *args, **kwargs):
        preview_data = request.session.get('bulk_update_preview', [])
        institution = request.user.profile.institution
        user_id = request.user.id
        # Use Celery for background processing to avoid blocking the request
        bulk_update_student_groups_task.delay(user_id, institution.id, preview_data)
        request.session.pop('bulk_update_preview', None)
        return HttpResponseRedirect(
            reverse('institution_admin:ticket_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
        )
    
    def dispatch(self, request, *args, **kwargs):
        registration_slug = self.kwargs.get('registration_slug')
        registration = get_object_or_404(Registration, slug=registration_slug)
        if registration.status:
            raise Http404("Bulk update is only allowed when registration is closed.")
        return super().dispatch(request, *args, **kwargs)