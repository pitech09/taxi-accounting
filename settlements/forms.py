from decimal import Decimal
from django import forms
from .models import DailySettlement


class DriverSettlementForm(forms.ModelForm):
    """Form for drivers to enter and submit settlements."""

    class Meta:
        model = DailySettlement
        fields = [
            'settlement_period', 'date', 'week_start', 'week_end',
            'cash_collected', 'mobile_collected', 'card_collected',
            'advance_income', 'other_income',
            'fuel_cost', 'toll_cost', 'border_fee',
            'repair_cost', 'driver_allowance', 'other_expenses',
            'driver_notes',
        ]
        widgets = {
            'settlement_period': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_settlement_period',
            }),
            'date': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control',
            }),
            'week_start': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control',
            }),
            'week_end': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control',
            }),
            'cash_collected': forms.NumberInput(attrs={
                'class': 'form-control income-input', 'step': '0.01', 'value': '0',
            }),
            'mobile_collected': forms.NumberInput(attrs={
                'class': 'form-control income-input', 'step': '0.01', 'value': '0',
            }),
            'card_collected': forms.NumberInput(attrs={
                'class': 'form-control income-input', 'step': '0.01', 'value': '0',
            }),
            'advance_income': forms.NumberInput(attrs={
                'class': 'form-control income-input', 'step': '0.01', 'value': '0',
            }),
            'other_income': forms.NumberInput(attrs={
                'class': 'form-control income-input', 'step': '0.01', 'value': '0',
            }),
            'fuel_cost': forms.NumberInput(attrs={
                'class': 'form-control expense-input', 'step': '0.01', 'value': '0',
            }),
            'toll_cost': forms.NumberInput(attrs={
                'class': 'form-control expense-input', 'step': '0.01', 'value': '0',
            }),
            'border_fee': forms.NumberInput(attrs={
                'class': 'form-control expense-input', 'step': '0.01', 'value': '0',
            }),
            'repair_cost': forms.NumberInput(attrs={
                'class': 'form-control expense-input', 'step': '0.01', 'value': '0',
            }),
            'driver_allowance': forms.NumberInput(attrs={
                'class': 'form-control expense-input', 'step': '0.01', 'value': '0',
            }),
            'other_expenses': forms.NumberInput(attrs={
                'class': 'form-control expense-input', 'step': '0.01', 'value': '0',
            }),
            'driver_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Notes for the owner (optional)',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('settlement_period')

        if period == 'daily' and not cleaned_data.get('date'):
            self.add_error('date', 'Date is required for daily settlement')

        if period == 'weekly':
            if not cleaned_data.get('week_start') or not cleaned_data.get('week_end'):
                self.add_error('week_start', 'Start and end date required for weekly settlement')
            if cleaned_data.get('week_start') and cleaned_data.get('week_end'):
                if cleaned_data['week_start'] > cleaned_data['week_end']:
                    self.add_error('week_end', 'End date must be after start date')

        # For weekly settlements, set the main date to the week_start
        if period == 'weekly' and cleaned_data.get('week_start'):
            cleaned_data['date'] = cleaned_data['week_start']

        return cleaned_data


class OwnerApprovalForm(forms.Form):
    """Form for owner to approve or reject a settlement."""

    action = forms.ChoiceField(
        choices=[('approve', 'Approve'), ('reject', 'Reject')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    owner_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Notes for the driver (required if rejecting)',
        }),
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        owner_notes = cleaned_data.get('owner_notes', '').strip()

        if action == 'reject' and not owner_notes:
            self.add_error('owner_notes', 'Owner notes are required when rejecting a settlement.')

        return cleaned_data


class OwnerSettlementForm(forms.ModelForm):
    """Form for owner to edit/override a settlement."""

    class Meta:
        model = DailySettlement
        fields = [
            'settlement_period', 'date', 'week_start', 'week_end',
            'cash_collected', 'mobile_collected', 'card_collected',
            'advance_income', 'other_income',
            'fuel_cost', 'toll_cost', 'border_fee',
            'repair_cost', 'driver_allowance', 'other_expenses',
            'payment_method', 'notes', 'owner_notes',
        ]
        widgets = {
            'settlement_period': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'week_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'week_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cash_collected': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mobile_collected': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'card_collected': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'advance_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fuel_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'toll_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'border_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'repair_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'driver_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_expenses': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'owner_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }