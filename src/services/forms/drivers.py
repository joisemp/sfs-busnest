"""
Forms for driver operations in the services app.

This module defines Django forms for driver operations, including refueling record management.
All forms use Bootstrap styling via a mixin for consistent UI.

Forms:
- DriverRefuelingRecordForm: For drivers to add refueling records for their assigned buses.
"""

from django import forms
from services.models import RefuelingRecord
from config.mixins import form_mixin


class DriverRefuelingRecordForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for drivers to add refueling records for their assigned buses.
    Fields: refuel_date, fuel_amount, fuel_cost, odometer_reading, fuel_type, notes
    """
    class Meta:
        model = RefuelingRecord
        fields = [
            'refuel_date', 'fuel_amount', 'fuel_cost', 'odometer_reading', 'fuel_type', 'notes'
        ]
        widgets = {
            'refuel_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes about this refueling...'}),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Customizes field labels and help text.
        """
        super(DriverRefuelingRecordForm, self).__init__(*args, **kwargs)
        self.fields['fuel_amount'].label = "Fuel Amount (Liters/kWh)"
        self.fields['fuel_amount'].widget.attrs['placeholder'] = 'e.g., 50.5'
        self.fields['fuel_cost'].label = "Total Cost (₹)"
        self.fields['fuel_cost'].widget.attrs['placeholder'] = 'e.g., 4500.00'
        self.fields['odometer_reading'].label = "Odometer Reading (km)"
        self.fields['odometer_reading'].widget.attrs['placeholder'] = 'e.g., 125000'
        self.fields['fuel_type'].label = "Fuel Type"
        self.fields['notes'].required = False
