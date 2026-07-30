from settlements.models import DailySettlement


def pending_approvals(request):
    """Make pending approvals count available in all owner templates."""
    if request.user.is_authenticated and request.user.is_staff:
        count = DailySettlement.objects.filter(status='submitted').count()
        return {'pending_approvals': count}
    return {}