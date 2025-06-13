"""
Forms for central admin operations in the services app.

This module defines Django forms for central admin operations, including creation and update forms for
people, institutions, buses, routes, stops, registrations, FAQs, schedules, schedule groups, bus records,
trips, and bus requests. All forms use Bootstrap styling via a mixin for consistent UI.

Forms:
- PeopleCreateForm: For creating user profiles, with email uniqueness validation.
- PeopleUpdateForm: For updating user profiles.
- InstitutionForm: For managing institutions.
- BusForm: For managing bus details, with custom label for availability.
- RouteForm: For managing routes, with custom field widget for route name.
- StopForm: For managing stops.
- RegistrationForm: For managing registrations, with custom label and switch for status.
- FAQForm: For managing FAQs.
- ScheduleForm: For managing schedules, with time input widgets.
- ScheduleGroupForm: For managing schedule groups, with custom label and switch for one-way booking.
- BusRecordCreateForm, BusRecordUpdateForm: For managing bus records.
- TripCreateForm: For creating trips.
- BusSearchForm: For searching buses by stop and schedule.
- BusRequestStatusForm: For managing bus request statuses.
- BusRequestCommentForm: For managing bus request comments.
- StopTransferForm: For transferring a stop to a new route, with queryset filtered by org and registration.
"""

from django import forms
from core.models import UserProfile, User
from services.models import Institution, Bus, Route, Stop, Registration, FAQ, Schedule, BusRecord, Trip, ScheduleGroup, BusRequest, BusRequestComment
from django.core.exceptions import ValidationError
from config.mixins import form_mixin


class PeopleCreateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for creating a user profile in the central admin interface.
    Validates that the email is unique among all users.
    Fields: email, first_name, last_name, is_central_admin, is_institution_admin
    """
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ['email', 'first_name', 'last_name', 'is_central_admin', 'is_institution_admin']  
    
    def clean_email(self):
        """
        Validates that the email does not already exist in the User model.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    
class PeopleUpdateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for updating a user profile in the central admin interface.
    Fields: first_name, last_name, is_central_admin, is_institution_admin
    """
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'is_central_admin', 'is_institution_admin']  


class InstitutionForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing institutions in the central admin interface.
    Fields: name, label, contact_no, email, incharge
    """
    class Meta:
        model = Institution
        fields = [
            'name', 'label', 'contact_no', 'email', 'incharge'
        ]
        

class BusForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing bus details in the central admin interface.
    Fields: registration_no, driver, capacity, is_available
    """
    class Meta:
        model = Bus
        fields = [
            'registration_no', 'driver', 'capacity', 'is_available'
        ]
    def __init__(self,*args,**kwargs):
        """
        Customizes the label and widget for the is_available field.
        """
        super(BusForm,self).__init__(*args,**kwargs)
        self.fields['is_available'].label="Available for service"
        self.fields['is_available'].is_switch = True


class RouteForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing routes in the central admin interface.
    Fields: name (with custom widget and label)
    """
    class Meta:
        model = Route
        fields = ['name']

    # Customizing the 'name' field
    name = forms.CharField(
        label='Route Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter the route name'
        }),
        max_length=200,
        required=True
    )




class StopForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing stops in the central admin interface.
    Fields: name
    """
    class Meta:
        model = Stop
        fields = [
            'name',
        ]


class RegistrationForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing registrations in the central admin interface.
    Fields: name, instructions, status (with custom label and switch)
    """
    class Meta:
        model = Registration
        fields = ['name', 'instructions', 'status']
        labels = {
            'status': 'Open registration',
        }
        
    def __init__(self,*args,**kwargs):
        """
        Customizes the status field to use a switch widget.
        """
        super(RegistrationForm, self).__init__(*args,**kwargs)
        self.fields['status'].is_switch = True
        

class FAQForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing FAQs in the central admin interface.
    Fields: question, answer
    """
    class Meta:
        model = FAQ
        fields = [
            'question', 'answer'
        ]


class ScheduleForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing schedules in the central admin interface.
    Fields: name, start_time, end_time (with time input widgets)
    """
    class Meta:
        model = Schedule
        fields = ['name', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
        

class ScheduleGroupForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing schedule groups in the central admin interface.
    Fields: pick_up_schedule, drop_schedule, description, allow_one_way (with custom label and switch)
    """
    class Meta:
        model = ScheduleGroup
        fields = ['pick_up_schedule', 'drop_schedule', 'description', 'allow_one_way']
    
    def __init__(self,*args,**kwargs):
        """
        Customizes the allow_one_way field to use a switch widget and label.
        """
        super(ScheduleGroupForm,self).__init__(*args,**kwargs)
        self.fields['allow_one_way'].label="Allow one way booking"
        self.fields['allow_one_way'].is_switch = True


class BusRecordCreateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for creating bus records in the central admin interface.
    Fields: label, bus
    """
    class Meta:
        model = BusRecord
        fields = ['label', 'bus']
        
    

class BusRecordUpdateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for updating bus records in the central admin interface.
    Fields: label, bus
    """
    class Meta:
        model = BusRecord
        fields = ['label', 'bus']
        
    
class TripCreateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for creating trips in the central admin interface.
    Fields: schedule, route
    """
    class Meta:
        model = Trip
        fields = ['schedule', 'route']
    

class BusSearchForm(form_mixin.BootstrapFormMixin, forms.Form):
    """
    Form for searching buses by stop and schedule in the central admin interface.
    Fields: stop, schedule
    """
    stop = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select stop'
    )
    schedule = forms.ModelChoiceField(
        queryset=Schedule.objects.all(),
        label="",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select timing'
    )


class BusRequestStatusForm(forms.ModelForm):
    """
    Form for managing bus request statuses in the central admin interface.
    Fields: status
    """
    class Meta:
        model = BusRequest
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class BusRequestCommentForm(forms.ModelForm):
    """
    Form for managing bus request comments in the central admin interface.
    Fields: comment
    """
    class Meta:
        model = BusRequestComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
        }

from services.models import Route

class StopTransferForm(forms.Form):
    """
    Form for transferring a stop to a new route in the central admin interface.
    Field: new_route (queryset filtered by org and registration)
    """
    new_route = forms.ModelChoiceField(
        queryset=Route.objects.none(),
        label="Select New Route",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        """
        Filters the new_route queryset by org and registration if provided.
        """
        org = kwargs.pop('org', None)
        registration = kwargs.pop('registration', None)
        super().__init__(*args, **kwargs)
        if org and registration:
            self.fields['new_route'].queryset = Route.objects.filter(org=org, registration=registration)