from django.contrib import admin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['name', 'plate', 'vehicle_type', 'operating_model', 'is_active']
    list_filter = ['vehicle_type', 'operating_model', 'is_active']
    search_fields = ['name', 'plate']