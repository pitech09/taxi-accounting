"""
Forms for the Settlements app.
"""
from django import forms
from .models import DailySettlement
from vehicles.models import Vehicle
from drivers.models import Driver


class DailySettlementForm(forms.ModelForm):
    """Form for drivers to enter daily or weekly settlements."""

    class Meta:
        model = DailySettlement
        fields = [
            'driver', 'vehicle', 'date', 'settlement_period',
            'week_start', 'week_end',
            'cash_collected', 'mobile_collected', 'card_collected',
            'fuel_expense', 'maintenance_expense', 'toll_expense',
            'other_expense', 'other_expense_desc',
            'driver_notes',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'week_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'week_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'settlement_period': forms.Select(attrs={'class': 'form-select', 'id': 'id_settlement_period'}),
            'driver': forms.Select(attrs={'class': 'form-select', 'id': 'id_driver'}),
            'vehicle': forms.Select(attrs={'class': 'form-select', 'id': 'id_vehicle'}),
            'cash_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'mobile_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'card_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'fuel_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'maintenance_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'toll_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'other_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'other_expense_desc': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '200'}),
            'driver_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        driver = kwargs.pop('driver', None)
        super().__init__(*args, **kwargs)

        if driver:
            # Restrict vehicle choices to the driver's assigned vehicle
            self.fields['driver'].widget = forms.HiddenInput()
            self.fields['vehicle'].widget = forms.HiddenInput()
            self.fields['driver'].initial = driver
            self.fields['vehicle'].initial = driver.vehicle

        # Make driver/vehicle not required at form level (set in view)
        self.fields['driver'].required = False
        self.fields['vehicle'].required = False

        # Add 'M' prefix styling via CSS class
        for field_name in ['cash_collected', 'mobile_collected', 'card_collected',
                           'fuel_expense', 'maintenance_expense', 'toll_expense', 'other_expense']:
            self.fields[field_name].widget.attrs['placeholder'] = '0.00'


class SettlementApprovalForm(forms.ModelForm):
    """Form for owners to approve or reject settlements."""

    class Meta:
        model = DailySettlement
        fields = ['status', 'owner_notes']
        widgets = {
            'status': forms.Select(choices=[
                ('approved', 'Approve'),
                ('rejected', 'Reject'),
            ], attrs={'class': 'form-select'}),
            'owner_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                  'placeholder': 'Enter notes for the driver...'}),
        }
