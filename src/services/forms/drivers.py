"""
Forms for driver operations in the services app.

This module defines Django forms for driver operations, including refueling record management.
All forms use Bootstrap styling via a mixin for consistent UI.

Forms:
- DriverRefuelingRecordForm: For drivers to add refueling records for their assigned buses.
"""

from django import forms
from services.models import RefuelingRecord, TripRecord
from config.mixins import form_mixin


class DriverTripRecordForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for drivers to add daily trip records (pickup/drop).
    Fields: record_date, actual_pickup_time, actual_drop_time, students_picked, students_dropped, odometer_reading, notes
    """
    class Meta:
        model = TripRecord
        fields = [
            'record_date', 'actual_pickup_time', 'actual_drop_time', 
            'students_picked', 'students_dropped', 'odometer_reading', 'notes'
        ]
        widgets = {
            'record_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_pickup_time': forms.TimeInput(attrs={'type': 'time'}),
            'actual_drop_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes about this trip...'}),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Customizes field labels and help text.
        """
        super(DriverTripRecordForm, self).__init__(*args, **kwargs)
        self.fields['record_date'].label = "Trip Date"
        self.fields['actual_pickup_time'].label = "Actual Pickup Time"
        self.fields['actual_pickup_time'].required = False
        self.fields['actual_drop_time'].label = "Actual Drop Time"
        self.fields['actual_drop_time'].required = False
        self.fields['students_picked'].label = "Students Picked Up"
        self.fields['students_picked'].required = False
        self.fields['students_picked'].widget.attrs['placeholder'] = 'Number of students'
        self.fields['students_dropped'].label = "Students Dropped"
        self.fields['students_dropped'].required = False
        self.fields['students_dropped'].widget.attrs['placeholder'] = 'Number of students'
        self.fields['odometer_reading'].label = "Odometer Reading (km)"
        self.fields['odometer_reading'].required = False
        self.fields['odometer_reading'].widget.attrs['placeholder'] = 'e.g., 125000'
        self.fields['notes'].required = False


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
