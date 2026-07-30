from django.contrib import admin
from .models import DailySettlement, DriverSettlementSchedule


@admin.register(DailySettlement)
class DailySettlementAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'driver', 'vehicle', 'operating_model', 'settlement_period',
        'status', 'total_income', 'driver_pay', 'total_owner_collected',
    ]
    list_filter = ['operating_model', 'status', 'settlement_period', 'date', 'debt_status']
    search_fields = ['driver__name', 'vehicle__name', 'driver_notes', 'owner_notes']
    date_hierarchy = 'date'
    readonly_fields = [
        'total_income', 'total_expenses', 'gross_profit', 'operating_model',
        'daily_quota', 'surplus_shortfall', 'debt_repaid', 'new_debt',
        'quota_paid_to_owner', 'daily_salary_earned', 'monthly_salary_accumulated',
        'driver_percentage', 'driver_percentage_amount', 'owner_percentage_amount',
        'contract_target', 'contract_monthly_gross', 'contract_remaining_target',
        'contract_driver_bonus', 'contract_driver_failure_amount', 'contract_is_success',
        'contract_bonus_type', 'contract_success_bonus_fixed',
        'contract_success_bonus_percentage', 'contract_failure_percentage',
        'contract_driver_pay', 'contract_owner_pay', 'driver_pay',
        'total_owner_collected', 'debt_status', 'submitted_at', 'approved_at',
    ]


@admin.register(DriverSettlementSchedule)
class DriverSettlementScheduleAdmin(admin.ModelAdmin):
    list_display = ['driver', 'frequency', 'week_start_day', 'effective_from', 'effective_to']
    list_filter = ['frequency']
    search_fields = ['driver__name']