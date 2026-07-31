"""
Context processors for the Taxi Accounting System.
"""
from settlements.models import DailySettlement
from accounts.models import SystemSettings


def pending_approvals(request):
    """Make pending approvals count available in all owner templates."""
    if request.user.is_authenticated and request.user.is_staff:
        count = DailySettlement.objects.filter(status='submitted').count()
        return {'pending_approvals': count}
    return {}


def system_settings(request):
    """Make system settings available in all templates."""
    try:
        settings = SystemSettings.get_settings()
        return {
            'company_name': settings.company_name,
            'company_phone': settings.company_phone,
            'company_email': settings.company_email,
            'company_address': settings.company_address,
            'company_logo': settings.company_logo,
        }
    except Exception:
        return {
            'company_name': 'Taxi Accounting System',
            'company_phone': '',
            'company_email': '',
            'company_address': '',
            'company_logo': None,
        }
