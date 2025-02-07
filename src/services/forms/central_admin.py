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


class BusRecordCreateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = BusRecord
        fields = ['label', 'bus']
        
    

class BusRecordUpdateForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = BusRecord
        fields = ['label', 'bus']
        
    

class BusSearchForm(form_mixin.BootstrapFormMixin, forms.Form):
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