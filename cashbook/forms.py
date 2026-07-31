"""
Forms for the Cashbook app.
"""
from django import forms
from .models import BankAccount, CashTransaction


class BankAccountForm(forms.ModelForm):
    """Form for adding/editing bank accounts."""

    class Meta:
        model = BankAccount
        fields = ['name', 'bank_name', 'account_number', 'branch',
                  'opening_balance', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main Operating Account'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. First National Bank'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CashTransactionForm(forms.ModelForm):
    """Form for recording any cash/bank transaction."""

    class Meta:
        model = CashTransaction
        fields = ['transaction_type', 'category', 'amount', 'date',
                  'bank_account', 'reference', 'receipt_photo', 'notes']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_transaction_type'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'receipt_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_account'].required = False
        self.fields['receipt_photo'].required = False
        self.fields['reference'].required = False


class ExpenseForm(forms.ModelForm):
    """Quick form for recording expenses."""

    class Meta:
        model = CashTransaction
        fields = ['transaction_type', 'category', 'amount', 'date',
                  'bank_account', 'reference', 'receipt_photo', 'notes']
        widgets = {
            'transaction_type': forms.Select(choices=[
                ('expense_cash', 'Expense (Cash)'),
                ('expense_bank', 'Expense (Bank)'),
                ('petty_cash', 'Petty Cash'),
            ], attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'receipt_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_account'].required = False
        self.fields['receipt_photo'].required = False
        self.fields['reference'].required = False


class DepositForm(forms.ModelForm):
    """Form for transferring cash to bank (deposit)."""

    class Meta:
        model = CashTransaction
        fields = ['bank_account', 'amount', 'date', 'reference', 'notes']
        widgets = {
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01', 'min': '0'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_account'].required = True
        self.fields['reference'].required = False
        self.fields['notes'].required = False
