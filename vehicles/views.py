"""
Vehicle views (shared).
Vehicle CRUD is handled in owner/views.py.
This module is kept for future shared vehicle logic.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from vehicles.models import Vehicle


@login_required
def vehicle_list(request):
    """List all vehicles."""
    vehicles = Vehicle.objects.all().order_by('name')
    return render(request, 'owner/vehicles/list.html', {'vehicles': vehicles})
