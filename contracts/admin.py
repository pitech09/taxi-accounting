from django.contrib import admin
from .models import MonthlyContractSummary

@admin.register(MonthlyContractSummary)
class MonthlyContractSummaryAdmin(admin.ModelAdmin):
    list_display = ['driver', 'vehicle', 'month', 'year', 'target', 'total_gross', 'is_success', 'driver_pay', 'owner_pay']
    list_filter = ['is_success', 'month', 'year']
    search_fields = ['driver__name', 'vehicle__name']