from django import forms
from core.models import UserProfile, User
from services.models import Institution, Bus, Route, Stop, Registration, FAQ, Schedule, BusRecord
from django.core.exceptions import ValidationError
from config.mixins import form_mixin


class PeopleCreateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ['email', 'first_name', 'last_name', 'is_central_admin', 'is_institution_admin']  
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    
class PeopleUpdateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'is_central_admin', 'is_institution_admin']  


class InstitutionForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Institution
        fields = [
            'name', 'label', 'contact_no', 'email', 'incharge'
        ]
        

class BusForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Bus
        fields = [
            'registration_no', 'driver', 'capacity', 'is_available'
        ]
    def __init__(self,*args,**kwargs):
        super(BusForm,self).__init__(*args,**kwargs)
        self.fields['is_available'].label="Available for service"
        self.fields['is_available'].is_switch = True


class RouteForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Route
        fields = ['name', 'stops']

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

    # Customizing the 'stops' field
    stops = forms.ModelMultipleChoiceField(
        queryset=Stop.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'size': '10',
        }),
        label="Select Stops",
        required=True,
        help_text="Hold Ctrl (Cmd) to select multiple stops"
    )

    # You could add custom validation or logic here if needed
    def clean_stops(self):
        stops = self.cleaned_data.get('stops')
        if not stops:
            raise forms.ValidationError("You must select at least one stop.")
        return stops


class StopForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Stop
        fields = [
            'name',
        ]


class RegistrationForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['name', 'instructions', 'status']
        labels = {
            'status': 'Open registration',
        }
        
    def __init__(self,*args,**kwargs):
        super(RegistrationForm, self).__init__(*args,**kwargs)
        self.fields['status'].is_switch = True
        

class FAQForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FAQ
        fields = [
            'question', 'answer'
        ]


class ScheduleForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['name', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class BusRecordForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = BusRecord
        fields = ['label', 'bus', 'route']
        
    def clean(self):
        cleaned_data = super().clean()
        bus = cleaned_data.get('bus')
        registration = cleaned_data.get('registration')  # Ensure this field exists in your model

        if bus and registration:
            # Check if a BusRecord with the same 'bus' and 'registration' already exists
            if BusRecord.objects.filter(bus=bus, registration=registration).exists():
                raise ValidationError("A record with this bus and registration already exists.")
        
        return cleaned_data