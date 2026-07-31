"""
Driver views (shared).
Driver CRUD is handled in owner/views.py.
This module is kept for future shared driver logic.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from drivers.models import Driver


@login_required
def driver_list(request):
    """List all drivers."""
    drivers = Driver.objects.all().order_by('name')
    return render(request, 'owner/drivers/list.html', {'drivers': drivers})
