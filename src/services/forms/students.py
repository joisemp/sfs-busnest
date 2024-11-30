from django import forms
from services.models import Stop, TimeSlot, Ticket
from config.mixins import form_mixin

class BusSearchForm(form_mixin.BootstrapFormMixin, forms.Form):
    stop = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select stop'
    )
    time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.all(),
        label="",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select timing'
    )
    

class ValidateStudentForm(form_mixin.BootstrapFormMixin, forms.Form):
    receipt_id = forms.CharField(max_length=100, required=True)
    student_id = forms.CharField(max_length=100, required=True)
    

class TicketForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    stop = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="Stop",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Ticket
        fields = [
            'institution', 'student_name', 'student_email', 'contact_no', 'alternative_contact_no', 'stop'
        ]

