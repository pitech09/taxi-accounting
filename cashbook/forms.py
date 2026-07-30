from decimal import Decimal
from django import forms
from .models import CashTransaction, BankAccount


class CashTransactionForm(forms.ModelForm):
    """Form for recording cash transactions."""

    class Meta:
        model = CashTransaction
        fields = [
            'transaction_type', 'category', 'amount', 'date',
            'bank_account', 'reference', 'receipt_photo', 'notes',
        ]
        widgets = {
            'transaction_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_transaction_type',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'id': 'id_amount',
                'placeholder': '0.00',
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'bank_account': forms.Select(attrs={
                'class': 'form-select',
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Receipt # or reference (optional)',
            }),
            'receipt_photo': forms.FileInput(attrs={
                'class': 'form-control',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_account'].queryset = BankAccount.objects.filter(is_active=True)
        self.fields['bank_account'].required = False

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        bank_account = cleaned_data.get('bank_account')
        amount = cleaned_data.get('amount')

        if amount and amount <= 0:
            self.add_error('amount', 'Amount must be greater than zero.')

        # Bank account is required for transfers and bank expenses
        if transaction_type in ('transfer_to_bank', 'transfer_from_bank', 'expense_bank') and not bank_account:
            self.add_error('bank_account', 'Bank account is required for this transaction type.')

        return cleaned_data


class BankAccountForm(forms.ModelForm):
    """Form for adding/editing bank accounts."""

    class Meta:
        model = BankAccount
        fields = [
            'name', 'account_number', 'bank_name', 'branch',
            'opening_balance', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Nedbank Business',
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account number',
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Nedbank',
            }),
            'branch': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Branch (optional)',
            }),
            'opening_balance': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'value': '0.00',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk:
            instance.current_balance = instance.opening_balance
        if commit:
            instance.save()
        return instance


class BankDepositForm(forms.Form):
    """Form for recording bank deposits (transfer from cash to bank)."""
    bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Bank Account',
    )
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'placeholder': '0.00',
        }),
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Deposit slip number (optional)',
        }),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2, 'placeholder': 'Notes (optional)',
        }),
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount


class BankWithdrawalForm(forms.Form):
    """Form for recording bank withdrawals (transfer from bank to cash)."""
    bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Bank Account',
    )
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'placeholder': '0.00',
        }),
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Reference (optional)',
        }),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2, 'placeholder': 'Notes (optional)',
        }),
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount


class ExpenseForm(forms.Form):
    """Form for recording business expenses."""
    CATEGORY_CHOICES = [
        ('fuel', 'Fuel'),
        ('maintenance', 'Maintenance/Repairs'),
        ('insurance', 'Insurance'),
        ('permit', 'Permit/License'),
        ('admin_expense', 'Admin Expense'),
        ('driver_salary', 'Driver Salary'),
        ('driver_commission', 'Driver Commission'),
        ('driver_bonus', 'Driver Bonus'),
        ('repayment', 'Loan Repayment'),
        ('other_expense', 'Other Expense'),
    ]

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
    ]

    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'placeholder': '0.00',
        }),
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_method'}),
    )
    bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Receipt # or reference (optional)',
        }),
    )
    receipt_photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2, 'placeholder': 'Notes (optional)',
        }),
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        bank_account = cleaned_data.get('bank_account')

        if payment_method == 'bank' and not bank_account:
            self.add_error('bank_account', 'Bank account is required for bank transfer payments.')

        return cleaned_data