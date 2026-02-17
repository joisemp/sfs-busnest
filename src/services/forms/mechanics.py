"""
mechanics.py - Forms for mechanic-related functionality

This module contains form classes used by mechanic users for:
- Bus maintenance record management
- Repair tracking
- Other mechanic-specific operations

All forms are scoped to the mechanic's organization.
"""

from django import forms
from services.models import Bus


class BusMaintenanceForm(forms.Form):
    """
    Form for recording bus maintenance activities.
    
    Fields can be extended as needed for specific maintenance tracking requirements.
    """
    bus = forms.ModelChoiceField(
        queryset=Bus.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Bus'
    )
    maintenance_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Maintenance Date'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label='Maintenance Notes',
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        org = kwargs.pop('org', None)
        super().__init__(*args, **kwargs)
        
        if org:
            self.fields['bus'].queryset = Bus.objects.filter(
                org=org,
                is_available=True
            ).order_by('registration_number')
