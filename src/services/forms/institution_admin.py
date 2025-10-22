"""
institution_admin.py - Forms for institution admin operations in the services app

This module defines Django forms for institution admin operations, including forms for receipts, student
groups, tickets, bus searches, and bulk student group updates. All forms use Bootstrap styling via a mixin
for a consistent UI.

Forms:
- ReceiptForm: For managing student payment receipts.
- StudentGroupForm: For managing student groups.
- TicketForm: For managing student tickets.
- BusSearchForm: For searching buses by pickup/drop points and schedule.
- BulkStudentGroupUpdateForm: For uploading Excel files to update student groups in bulk.
"""

from django import forms
from config.mixins import form_mixin
from services.models import Receipt, StudentGroup, Ticket, Stop, Schedule, BusReservationRequest


class ReceiptForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing student payment receipts in the institution admin interface.
    Fields: registration, receipt_id, student_id, student_group
    """
    class Meta:
        model = Receipt
        fields = ['registration', 'receipt_id', 'student_id', 'student_group']
        
        
class StudentGroupForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing student groups in the institution admin interface.
    Fields: name
    """
    class Meta:
        model = StudentGroup
        fields = ['name',]
        
        
class TicketForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing student tickets in the institution admin interface.
    Fields: institution, student_group, student_name, student_email, contact_no, alternative_contact_no, status
    """
    class Meta:
        model = Ticket
        fields = ['institution', 'student_group', 'student_name', 'student_email', 'contact_no', 'alternative_contact_no', 'status']
        
        
class BusSearchForm(form_mixin.BootstrapFormMixin, forms.Form):
    """
    Form for searching buses by pickup/drop points and schedule in the institution admin interface.
    Fields: pickup_point, drop_point, schedule
    """
    pickup_point = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select pickup point'
    )
    drop_point = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select drop point'
    )
    schedule = forms.ModelChoiceField(
        queryset=Schedule.objects.all(),
        label="",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select timing'
    )

class BulkStudentGroupUpdateForm(forms.Form):
    """
    Form for uploading Excel files to update student groups in bulk in the institution admin interface.
    Field: file (Excel file upload)
    """
    file = forms.FileField(label="Upload Excel file", required=True)


class BusReservationRequestForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for creating bus reservation requests in the institution admin interface.
    Fields: date, booked_by, contact_number, from_location, to_location, 
            departure_time, arrival_time, requested_capacity, purpose, notes
    """
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Date of the reservation"
    )
    departure_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text="Departure time"
    )
    arrival_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text="Arrival time"
    )
    
    class Meta:
        model = BusReservationRequest
        fields = [
            'date', 'booked_by', 'contact_number', 'from_location', 'to_location',
            'departure_time', 'arrival_time', 'requested_capacity', 'purpose', 'notes'
        ]
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
