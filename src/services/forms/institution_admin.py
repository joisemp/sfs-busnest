from django import forms
from config.mixins import form_mixin
from services.models import Receipt


class ReceiptForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['registration', 'receipt_id', 'student_id', 'student_group']