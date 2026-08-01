from django import forms
from .models import Loan, LoanPayment


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            'loan_type', 'driver', 'amount', 'interest_rate', 'interest_method',
            'interest_frequency', 'start_date', 'expected_repayment_date', 'purpose', 'notes'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_repayment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class LoanPaymentForm(forms.ModelForm):
    class Meta:
        model = LoanPayment
        fields = ['amount', 'date', 'payment_method', 'reference', 'notes', 'bank_account']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }