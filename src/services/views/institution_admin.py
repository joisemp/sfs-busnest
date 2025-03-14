import threading
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, DeleteView, UpdateView, FormView, View
from django.urls import reverse, reverse_lazy
from services.forms.students import StopSelectForm
from services.models import Bus, BusRecord, Registration, Receipt, ScheduleGroup, Stop, StudentGroup, Ticket, Schedule, ReceiptFile, Trip
from services.forms.institution_admin import ReceiptForm, StudentGroupForm, TicketForm, BusSearchForm
from config.mixins.access_mixin import InsitutionAdminOnlyAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from services.tasks import process_uploaded_receipt_data_excel, export_tickets_to_excel
from services.utils import get_filtered_bus_records

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
        schedule = self.request.GET.get('schedule')
        student_group = self.request.GET.get('student_group')
        filters = False  # Default no filters applied

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
        process_uploaded_receipt_data_excel.delay(self.request.user, receipt_data_file.file.name, user.profile.org.id, user.profile.institution.id, receipt_data_file.registration.id)
        return redirect(reverse('institution_admin:receipt_list'))
    
    
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
#         student_group = self.request.GET.getlist('student_group')
        
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
#         if student_group and not student_group == ['']:
#             queryset = queryset.filter(student_group_id__in=student_group)
        
#         # Send the filtered queryset to the Celery task for export
#         # export_tickets_to_excel.apply_async(
#         #     args=[request.user.id, registration_slug, search_term, {
#         #         'institution': institution,
#         #         'pickup_points': pickup_points,
#         #         'drop_points': drop_points,
#         #         'schedule': schedule,
#         #         'pickup_buses': pickup_buses,
#         #         'drop_buses': drop_buses,
#         #         'student_group': student_group,
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
        student_group = request.GET.getlist('student_group')

        filters = {
            'institution': institution,
            'pickup_points': pickup_points,
            'drop_points': drop_points,
            'schedule': schedule,
            'pickup_buses': pickup_buses,
            'drop_buses': drop_buses,
            'student_group': student_group,
        }

        return export_tickets_to_excel(request.user.id, registration_slug, search_term, filters)
    
    
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
        schedules = Schedule.objects.all()
        query_string = self.request.GET.get('type', '')
        type = query_string if query_string else 'pickup and drop'
        return render(request, self.template_name, {'schedules': schedules, 'type': type})

    def post(self, request, registration_code, ticket_id):
        selected_id = request.POST.get("schedule_group")

        if not selected_id:
            schedules = Schedule.objects.all()
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
            existing_trip = Trip.objects.get(registration=registration, record=ticket.pickup_bus_record, schedule=ticket.pickup_schedule)
            ticket.pickup_bus_record = bus_record
            ticket.pickup_point = pickup_point
            ticket.pickup_schedule = schedule
            existing_trip.booking_count -= 1
            existing_trip.save()
            new_trip.booking_count += 1
            new_trip.save()
        
        elif change_type == 'drop':
            new_trip = Trip.objects.get(registration=registration, record=bus_record, schedule=schedule)
            existing_trip = Trip.objects.get(registration=registration, record=ticket.drop_bus_record, schedule=ticket.drop_schedule)
            ticket.drop_bus_record = bus_record
            ticket.drop_point = drop_point
            ticket.drop_schedule = schedule
            existing_trip.booking_count -= 1
            existing_trip.save()
            new_trip.booking_count += 1
            new_trip.save()
        
        ticket.save()
        
        return redirect(
            reverse('institution_admin:ticket_list', 
                    kwargs={'registration_slug': registration.slug}
                )
            )
