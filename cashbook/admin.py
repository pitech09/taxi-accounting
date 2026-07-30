from django.contrib import admin
from .models import CashInHand, BankAccount, CashTransaction, DailyCashBook


@admin.register(CashInHand)
class CashInHandAdmin(admin.ModelAdmin):
    list_display = ['id', 'balance', 'last_updated']
    readonly_fields = ['last_updated']


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'bank_name', 'account_number', 'current_balance', 'is_active']
    list_filter = ['is_active', 'bank_name']
    search_fields = ['name', 'account_number', 'bank_name']
    readonly_fields = ['created_at']


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'transaction_type', 'category', 'amount', 'bank_account', 'settlement']
    list_filter = ['transaction_type', 'category', 'date', 'bank_account']
    search_fields = ['reference', 'notes', 'settlement__driver__name']
    date_hierarchy = 'date'
    readonly_fields = ['cash_balance_after', 'bank_balance_after', 'created_at']


@admin.register(DailyCashBook)
class DailyCashBookAdmin(admin.ModelAdmin):
    list_display = ['date', 'opening_balance', 'total_cash_in', 'total_cash_out', 'closing_balance', 'net_cash_flow']
    list_filter = ['date']
    readonly_fields = ['created_at', 'updated_at']