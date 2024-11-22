from django import forms
from services.models import Stop, TimeSlot

class BusSearchForm(forms.Form):
    pickup_point = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="Pickup Point",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    drop_point = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        label="Drop Point",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.all(),
        label="Timing",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

