from django import forms
from config.mixins import form_mixin
from services.models import Receipt, StudentGroup, Ticket


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
        fields = ['recipt', 'student_id', 'institution', 'student_group', 'bus', 'student_name', 'student_email', 'contact_no', 'alternative_contact_no', 'pickup_point', 'drop_point', 'time_slot', 'status']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable the 'recipt' and 'student_id' fields
        self.fields['recipt'].disabled = True
        self.fields['student_id'].disabled = True
        
        
        