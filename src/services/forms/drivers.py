"""
Forms for driver operations in the services app.

This module defines Django forms for driver operations, including refueling record management.
All forms use Bootstrap styling via a mixin for consistent UI.
Date and time values are automatically captured when records are submitted.

Forms:
- DriverTripRecordForm: For drivers to add daily trip records (pickup or drop).
- DriverRefuelingRecordForm: For drivers to add refueling records for their assigned buses.
"""

from django import forms
from django.utils import timezone
from services.models import RefuelingRecord, TripRecord
from config.mixins import form_mixin


class DriverTripRecordForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for drivers to add daily trip records (pickup or drop).
    Date and time are automatically captured when the record is submitted.
    Fields: trip_type, odometer_reading, notes
    """
    class Meta:
        model = TripRecord
        fields = ['trip_type', 'odometer_reading', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes about this trip...'}),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Customizes field labels and help text.
        Accepts optional 'bus' kwarg for duplicate validation.
        """
        self.bus = kwargs.pop('bus', None)
        super(DriverTripRecordForm, self).__init__(*args, **kwargs)
        self.fields['trip_type'].label = "Trip Type"
        self.fields['trip_type'].help_text = "Pickup: When taking bus to start work | Drop: When parking bus after work"
        self.fields['odometer_reading'].label = "Odometer Reading (km)"
        self.fields['odometer_reading'].widget.attrs['placeholder'] = 'e.g., 125045'
        self.fields['odometer_reading'].help_text = "Current odometer reading from dashboard"
        self.fields['notes'].required = False
    
    def clean_trip_type(self):
        """
        Validate that a record doesn't already exist for this bus, date, and trip type.
        For updates, exclude the current instance from the check.
        """
        trip_type = self.cleaned_data.get('trip_type')
        
        if self.bus:
            # For new records, use today's date. For updates, use the existing record_date
            if self.instance.pk:
                record_date = self.instance.record_date
            else:
                record_date = timezone.localtime(timezone.now()).date()
            
            # Check for existing records, excluding the current instance if updating
            existing_query = TripRecord.objects.filter(
                bus=self.bus,
                record_date=record_date,
                trip_type=trip_type
            )
            
            # Exclude current instance when updating
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            
            if existing_query.exists():
                trip_type_display = "Pickup" if trip_type == 'pickup' else "Drop"
                raise forms.ValidationError(
                    f"A {trip_type_display} trip record already exists for this bus on {record_date}. "
                    f"You can only have one {trip_type_display} record per day."
                )
        
        return trip_type


class DriverRefuelingRecordForm(form_mixin.BootstrapFormMixin, forms.ModelForm):
    """
    Form for drivers to add refueling records for their assigned buses.
    Date is automatically captured when the record is submitted.
    Fields: fuel_amount, fuel_cost, odometer_reading, fuel_type, notes
    """
    class Meta:
        model = RefuelingRecord
        fields = ['fuel_amount', 'fuel_cost', 'odometer_reading', 'fuel_type', 'notes']
        widgets = {
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
