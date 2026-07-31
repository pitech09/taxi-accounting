from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import DailySettlement

# Try to import DriverSettlementSchedule if it exists
try:
    from .models import DriverSettlementSchedule
except ImportError:
    DriverSettlementSchedule = None


@admin.register(DailySettlement)
class DailySettlementAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'driver', 'vehicle', 'operating_model', 'settlement_period',
        'status', 'total_income', 'driver_pay', 'total_owner_collected',
    ]
    list_filter = [
        'operating_model', 'status', 'settlement_period', 'date', 'debt_status'
    ]
    search_fields = [
        'driver__name', 'vehicle__name', 'driver_notes', 'owner_notes'
    ]
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
        'cash_added_to_hand', 'cash_transaction_created',
    ]
    fieldsets = (
        (None, {
            'fields': (
                'driver', 'vehicle', 'date', 'settlement_period',
                'week_start', 'week_end', 'status',
            )
        }),
        ('Income & Expenses', {
            'fields': (
                'cash_collected', 'mobile_collected', 'card_collected',
                'fuel_expense', 'maintenance_expense', 'toll_expense',
                'other_expense', 'other_expense_desc',
            )
        }),
        ('Notes & Workflow', {
            'fields': ('driver_notes', 'owner_notes', 'submitted_at', 'approved_at', 'approved_by'),
            'classes': ('collapse',),
        }),
        ('Calculations', {
            'fields': (
                'total_income', 'total_expenses', 'gross_profit',
                'operating_model', 'driver_pay', 'total_owner_collected',
            ),
            'classes': ('collapse',),
        }),
        ('Quota Model Fields', {
            'fields': (
                'daily_quota', 'surplus_shortfall', 'debt_repaid', 'new_debt',
                'quota_paid_to_owner', 'debt_status',
            ),
            'classes': ('collapse',),
        }),
        ('Salary Model Fields', {
            'fields': (
                'daily_salary_earned', 'monthly_salary_accumulated',
            ),
            'classes': ('collapse',),
        }),
        ('Percentage Model Fields', {
            'fields': (
                'driver_percentage', 'driver_percentage_amount',
                'owner_percentage_amount',
            ),
            'classes': ('collapse',),
        }),
        ('Contract Model Fields', {
            'fields': (
                'contract_target', 'contract_monthly_gross',
                'contract_remaining_target', 'contract_driver_bonus',
                'contract_driver_failure_amount', 'contract_is_success',
                'contract_bonus_type', 'contract_success_bonus_fixed',
                'contract_success_bonus_percentage', 'contract_failure_percentage',
                'contract_driver_pay', 'contract_owner_pay',
            ),
            'classes': ('collapse',),
        }),
        ('Cash Integration', {
            'fields': ('cash_added_to_hand', 'cash_transaction_created'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        try:
            obj.full_clean()
        except ValidationError as e:
            raise ValidationError(e.message_dict)
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'approved':
            return [f.name for f in self.model._meta.fields if f.name not in ['id', 'created_at', 'updated_at']]
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == 'approved':
            return False
        return super().has_delete_permission(request, obj)


# Only register DriverSettlementSchedule if the model exists
if DriverSettlementSchedule is not None:
    @admin.register(DriverSettlementSchedule)
    class DriverSettlementScheduleAdmin(admin.ModelAdmin):
        list_display = ['driver', 'frequency', 'week_start_day', 'effective_from', 'effective_to']
        list_filter = ['frequency']
        search_fields = ['driver__name']