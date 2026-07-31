"""
Settlement views (shared between owner and driver portals).
Currently handled by owner/views.py and driver_portal/views.py.
This module is kept for future shared settlement logic.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def settlement_list(request):
    """List all settlements (shared view)."""
    from settlements.models import DailySettlement
    settlements = DailySettlement.objects.all().order_by('-date')
    return render(request, 'owner/settlements/list.html', {'settlements': settlements})
