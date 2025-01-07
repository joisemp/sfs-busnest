from django import forms
from services.models import Stop, Schedule, Ticket, BusRequest
from config.mixins import form_mixin

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
            'student_name', 'student_email', 'contact_no', 'alternative_contact_no', 'stop'
        ]


class BusRequestForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = BusRequest
        fields = [
            "student_name", "pickup_address", "drop_address", "contact_no", "contact_email"
            ]