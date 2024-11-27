from django import forms
from core.models import UserProfile, User
from services.models import Institution, Bus, Route, Stop, Registration, FAQ
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
            'label', 'bus_no', 'route', 'driver', 'time_slot'
        ]


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
            'name', 'map_link'
        ]


class RegistrationForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['name', 'instructions', 'stops', 'status']
        labels = {
            'status': 'Open registration',
        }
    
    # Customizing the 'stops' field
    stops = forms.ModelMultipleChoiceField(
        queryset=Stop.objects.all(),
        widget=forms.SelectMultiple(attrs={'size': '10'}),
        label="Select Stops",
        required=True,
        help_text="Hold Ctrl (Cmd) to select multiple stops"
    )
        
    def clean_stops(self):
        stops = self.cleaned_data.get('stops')
        if not stops:
            raise forms.ValidationError("You must select at least one stop.")
        return stops


class FAQForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FAQ
        fields = [
            'question', 'answer'
        ]
