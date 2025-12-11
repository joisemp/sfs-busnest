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
from services.models import Receipt, StudentGroup, Ticket, Stop, Schedule, BusReservationRequest, Payment, InstallmentDate


class ReceiptForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for managing student payment receipts in the institution admin interface.
    Fields: registration, receipt_id, student_id, student_group
    
    The student_group field is filtered to show only groups belonging to the specified institution.
    """
    
    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if institution:
            # Filter student groups to only show groups from the institution
            self.fields['student_group'].queryset = StudentGroup.objects.filter(institution=institution)
    
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
    
    The student_group field is filtered to show only groups belonging to the specified institution.
    """
    
    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if institution:
            # Filter student groups to only show groups from the institution
            self.fields['student_group'].queryset = StudentGroup.objects.filter(institution=institution)
    
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
    departure_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Departure date and time",
        label="Departure Date & Time"
    )
    arrival_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Arrival date and time",
        label="Arrival Date & Time"
    )
    
    class Meta:
        model = BusReservationRequest
        fields = [
            'booked_by', 'contact_number', 'from_location', 'to_location',
            'requested_capacity', 'purpose', 'notes'
        ]
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        """
        Validate that arrival datetime is after departure datetime.
        """
        cleaned_data = super().clean()
        departure_datetime = cleaned_data.get('departure_datetime')
        arrival_datetime = cleaned_data.get('arrival_datetime')
        
        if departure_datetime and arrival_datetime:
            if arrival_datetime <= departure_datetime:
                raise forms.ValidationError(
                    "Arrival date and time must be after departure date and time."
                )
        
        return cleaned_data


class PaymentForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for recording payments for student tickets in the institution admin interface.
    Fields: installment_date, amount, payment_date, payment_mode, transaction_reference, notes
    
    Note: The ticket is obtained from the URL parameter and set in the view, not from the form.
    """
    
    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        registration = kwargs.pop('registration', None)
        self.ticket = kwargs.pop('ticket', None)  # Store ticket for validation
        super().__init__(*args, **kwargs)
        
        if institution:
            # Filter tickets to only show tickets from the institution (not used in form anymore)
            pass
            
        if registration:
            # Filter installment dates to only show those for the registration
            self.fields['installment_date'].queryset = InstallmentDate.objects.filter(
                registration=registration
            ).order_by('due_date')
        else:
            self.fields['installment_date'].queryset = InstallmentDate.objects.none()
    
    def clean(self):
        """
        Validate that no duplicate payment exists for the same ticket and installment.
        """
        cleaned_data = super().clean()
        installment_date = cleaned_data.get('installment_date')
        
        # Check if ticket and installment_date combination already exists
        if self.ticket and installment_date:
            # Exclude current instance if editing
            existing_payment = Payment.objects.filter(
                ticket=self.ticket,
                installment_date=installment_date
            )
            if self.instance and self.instance.pk:
                existing_payment = existing_payment.exclude(pk=self.instance.pk)
            
            if existing_payment.exists():
                payment = existing_payment.first()
                raise forms.ValidationError(
                    f"A payment (ID: {payment.payment_id}) already exists for this ticket and installment date. "
                    f"Please select a different installment or edit the existing payment."
                )
        
        return cleaned_data
    
    class Meta:
        model = Payment
        fields = ['installment_date', 'amount', 'payment_date', 'payment_mode', 'transaction_reference', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
