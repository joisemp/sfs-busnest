from django import forms
from services.models import Stop, TimeSlot
from config.mixins import form_mixin

class BusSearchForm(form_mixin.BootstrapFormMixin, forms.Form):
    pickup_point = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="Pickup Point",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    drop_point = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="Drop Point",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.all(),
        label="Timing",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    

class ValidateStudentForm(forms.Form):
    recipt_id = forms.CharField(max_length=100, required=True)
    student_id = forms.CharField(max_length=100, required=True)
    
