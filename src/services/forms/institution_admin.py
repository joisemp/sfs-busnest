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
        fields = ['institution', 'student_group', 'bus', 'student_name', 'student_email', 'contact_no', 'alternative_contact_no', 'pickup_point', 'drop_point', 'time_slot', 'status']
        
        
        