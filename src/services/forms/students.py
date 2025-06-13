"""
students.py - Forms for student operations in the services app

This module defines Django forms for student-related operations, including selecting stops, validating students,
creating tickets, and submitting bus requests. All forms use Bootstrap styling via a mixin for a consistent UI.

Forms:
- StopSelectForm: For selecting a stop from available options.
- ValidateStudentForm: For validating student identity using receipt and student IDs.
- TicketForm: For creating or updating student ticket information.
- BusRequestForm: For submitting bus requests by students.
"""

from django import forms
from services.models import ScheduleGroup, Stop, Schedule, Ticket, BusRequest, Trip
from config.mixins import form_mixin

class StopSelectForm(form_mixin.BootstrapFormMixin, forms.Form):
    """
    Form for students to select a stop from available options.

    Fields:
        stop (ModelChoiceField): The stop selected by the student. Uses a searchable select widget.
    """
    stop = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control select2-searchable'}),
        empty_label='Select stop'
    )
    

class ValidateStudentForm(form_mixin.BootstrapFormMixin, forms.Form):
    """
    Form for validating a student's identity using receipt and student IDs.

    Fields:
        receipt_id (CharField): The payment receipt ID for validation.
        student_id (CharField): The unique student ID for validation.
    """
    receipt_id = forms.CharField(max_length=100, required=True)
    student_id = forms.CharField(max_length=100, required=True)
    

class TicketForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    ModelForm for creating or updating student ticket information.

    Fields:
        student_name (CharField): Name of the student.
        student_email (EmailField): Email address of the student.
        contact_no (CharField): Primary contact number.
        alternative_contact_no (CharField): Alternative contact number.
        pickup_point (ForeignKey): Pickup stop for the ticket.
        drop_point (ForeignKey): Drop stop for the ticket.
    """
    class Meta:
        model = Ticket
        fields = [
            'student_name', 'student_email', 'contact_no', 'alternative_contact_no', 'pickup_point', 'drop_point'
        ]          


class BusRequestForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    ModelForm for students to submit a bus request.

    Fields:
        student_name (CharField): Name of the student making the request.
        pickup_address (CharField): Address where the student wishes to be picked up.
        drop_address (CharField): Address where the student wishes to be dropped off.
        contact_no (CharField): Contact number for the student.
        contact_email (EmailField): Email address for the student.
    """
    class Meta:
        model = BusRequest
        fields = [
            "student_name", "pickup_address", "drop_address", "contact_no", "contact_email"
        ]