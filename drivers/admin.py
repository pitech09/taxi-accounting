from django.contrib import admin
from .models import Driver

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['name', 'driver_code', 'phone', 'vehicle', 'is_active', 'is_portal_enabled']
    list_filter = ['is_active', 'is_portal_enabled']
    search_fields = ['name', 'phone', 'id_number', 'driver_code']
