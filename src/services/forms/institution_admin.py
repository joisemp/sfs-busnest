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
from services.models import Receipt, StudentGroup, Ticket, Stop, Schedule


class ReceiptForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['registration', 'receipt_id', 'student_id', 'student_group']
        
        
class StudentGroupForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = StudentGroup
        fields = ['name',]
        
        
class TicketForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['institution', 'student_group', 'student_name', 'student_email', 'contact_no', 'alternative_contact_no', 'status']
        
        
class BusSearchForm(form_mixin.BootstrapFormMixin, forms.Form):
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
    file = forms.FileField(label="Upload Excel file", required=True)