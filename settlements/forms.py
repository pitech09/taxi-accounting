"""
Forms for the Settlements app.

Includes:
- DailySettlementForm: for drivers to submit settlements.
- SettlementApprovalForm: for owners to approve/reject.
- SettlementAdminForm: for owners to create/edit settlements on behalf of drivers.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import DailySettlement
from vehicles.models import Vehicle
from drivers.models import Driver


class DailySettlementForm(forms.ModelForm):
    """
    Form for drivers to enter daily or weekly settlements.

    - Driver and vehicle are automatically set from the logged‑in driver.
    - Status is always set to 'submitted' in the view.
    - Amounts are validated to be non‑negative.
    - Weekly period requires week_start and week_end.
    """

    class Meta:
        model = DailySettlement
        fields = [
            'date', 'settlement_period',
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
            'cash_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'mobile_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'card_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'fuel_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'maintenance_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'toll_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'other_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'other_expense_desc': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '200'}),
            'driver_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Remove driver/vehicle from kwargs – we'll set them separately
        self.driver = kwargs.pop('driver', None)
        super().__init__(*args, **kwargs)

        # Remove driver and vehicle from the form – they're set in the view
        self.fields.pop('driver', None)
        self.fields.pop('vehicle', None)

        # Add a hidden field for the driver ID (will be set in the view)
        # Not needed – we'll handle it in the view logic.

        # Set default period to daily if not specified
        if not self.instance.pk and not self.initial.get('settlement_period'):
            self.initial['settlement_period'] = 'daily'

    def clean_cash_collected(self):
        return self._clean_amount('cash_collected')

    def clean_mobile_collected(self):
        return self._clean_amount('mobile_collected')

    def clean_card_collected(self):
        return self._clean_amount('card_collected')

    def clean_fuel_expense(self):
        return self._clean_amount('fuel_expense')

    def clean_maintenance_expense(self):
        return self._clean_amount('maintenance_expense')

    def clean_toll_expense(self):
        return self._clean_amount('toll_expense')

    def clean_other_expense(self):
        return self._clean_amount('other_expense')

    def _clean_amount(self, field_name):
        value = self.cleaned_data.get(field_name)
        if value is None:
            return 0
        if value < 0:
            raise ValidationError(f'{field_name.replace("_", " ").title()} cannot be negative.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('settlement_period')

        if period == 'weekly':
            week_start = cleaned_data.get('week_start')
            week_end = cleaned_data.get('week_end')
            if not week_start or not week_end:
                self.add_error('week_start', 'Start and end dates are required for weekly settlements.')
                self.add_error('week_end', 'Start and end dates are required for weekly settlements.')
            elif week_start > week_end:
                self.add_error('week_end', 'End date must be after start date.')

        elif period == 'daily':
            # For daily, ensure a date is provided
            if not cleaned_data.get('date'):
                self.add_error('date', 'Date is required for daily settlements.')

        return cleaned_data


class SettlementAdminForm(forms.ModelForm):
    """
    Form for owners to create or edit settlements on behalf of drivers.

    Includes driver and vehicle selection, and status can be set
    (useful for correcting/approving settlements).
    """

    class Meta:
        model = DailySettlement
        fields = [
            'driver', 'vehicle', 'date', 'settlement_period',
            'week_start', 'week_end',
            'cash_collected', 'mobile_collected', 'card_collected',
            'fuel_expense', 'maintenance_expense', 'toll_expense',
            'other_expense', 'other_expense_desc',
            'driver_notes', 'status',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'week_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'week_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'settlement_period': forms.Select(attrs={'class': 'form-select'}),
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'cash_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'mobile_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'card_collected': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'fuel_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'maintenance_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'toll_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'other_expense': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'other_expense_desc': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '200'}),
            'driver_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['driver'].queryset = Driver.objects.filter(is_active=True)
        self.fields['vehicle'].queryset = Vehicle.objects.filter(is_active=True)

        # Set default status to 'submitted' for new settlements
        if not self.instance.pk:
            self.initial['status'] = 'submitted'

    def clean_cash_collected(self):
        return self._clean_amount('cash_collected')

    def clean_mobile_collected(self):
        return self._clean_amount('mobile_collected')

    def clean_card_collected(self):
        return self._clean_amount('card_collected')

    def clean_fuel_expense(self):
        return self._clean_amount('fuel_expense')

    def clean_maintenance_expense(self):
        return self._clean_amount('maintenance_expense')

    def clean_toll_expense(self):
        return self._clean_amount('toll_expense')

    def clean_other_expense(self):
        return self._clean_amount('other_expense')

    def _clean_amount(self, field_name):
        value = self.cleaned_data.get(field_name)
        if value is None:
            return 0
        if value < 0:
            raise ValidationError(f'{field_name.replace("_", " ").title()} cannot be negative.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('settlement_period')

        if period == 'weekly':
            week_start = cleaned_data.get('week_start')
            week_end = cleaned_data.get('week_end')
            if not week_start or not week_end:
                self.add_error('week_start', 'Start and end dates are required for weekly settlements.')
                self.add_error('week_end', 'Start and end dates are required for weekly settlements.')
            elif week_start > week_end:
                self.add_error('week_end', 'End date must be after start date.')

        elif period == 'daily':
            if not cleaned_data.get('date'):
                self.add_error('date', 'Date is required for daily settlements.')

        # Validate that the selected driver is assigned to the selected vehicle
        driver = cleaned_data.get('driver')
        vehicle = cleaned_data.get('vehicle')
        if driver and vehicle and driver.vehicle != vehicle:
            self.add_error('vehicle', f'{driver.name} is not assigned to this vehicle.')

        return cleaned_data


class SettlementApprovalForm(forms.Form):
    """
    Simple approval form for owners to approve/reject a settlement.
    Uses a Form (not ModelForm) to avoid accidentally updating other fields.
    """
    action = forms.ChoiceField(
        choices=[('approve', 'Approve'), ('reject', 'Reject')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Action',
    )
    owner_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter notes for the driver...'}),
        label='Notes for Driver',
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        owner_notes = cleaned_data.get('owner_notes')

        # If rejecting, require notes
        if action == 'reject' and not owner_notes:
            self.add_error('owner_notes', 'Please provide a reason for rejecting this settlement.')

        return cleaned_data


class SettlementFilterForm(forms.Form):
    """
    Filter form for the settlement list view (owner only).
    """
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(DailySettlement.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(is_active=True),
        required=False,
        empty_label='All Vehicles',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    driver = forms.ModelChoiceField(
        queryset=Driver.objects.filter(is_active=True),
        required=False,
        empty_label='All Drivers',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='From Date',
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='To Date',
    )