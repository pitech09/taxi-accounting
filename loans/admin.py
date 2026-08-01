"""
Admin configuration for the loans app.
"""
from django.contrib import admin
from .models import Loan, LoanPayment, LoanInterest


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan_type', 'driver', 'amount', 'outstanding_balance',
                    'interest_rate', 'interest_method', 'status', 'start_date']
    list_filter = ['loan_type', 'status', 'interest_method', 'interest_frequency',
                   'start_date', 'created_at']
    search_fields = ['driver__name', 'purpose', 'notes']
    readonly_fields = ['total_paid', 'total_interest_accrued', 'created_at', 'updated_at']

    fieldsets = [
        ('Loan Details', {
            'fields': ['loan_type', 'driver', 'amount', 'outstanding_balance',
                       'purpose', 'notes']
        }),
        ('Interest Settings', {
            'fields': ['interest_rate', 'interest_method', 'interest_frequency',
                       'start_date', 'expected_repayment_date', 'last_interest_date']
        }),
        ('Status', {
            'fields': ['status']
        }),
        ('Tracking', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan', 'amount', 'date', 'payment_method', 'reference']
    list_filter = ['payment_method', 'date', 'created_at']
    search_fields = ['loan__driver__name', 'reference', 'notes']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'


@admin.register(LoanInterest)
class LoanInterestAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan', 'amount', 'date', 'note']
    list_filter = ['date', 'created_at']
    search_fields = ['loan__driver__name', 'note']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
