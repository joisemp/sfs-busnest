from django import forms
from core.models import UserProfile, User
from services.models import Institution, Bus
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