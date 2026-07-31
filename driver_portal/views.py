"""
Driver portal views.
Drivers authenticate with their 4-digit driver code and portal password.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
import calendar
from django.db.models import Sum
from drivers.models import Driver
from settlements.models import DailySettlement
from settlements.forms import DailySettlementForm
from cashbook.models import CashTransaction
from accounts.models import SystemSettings


# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------
def login(request):
    """Driver login using driver_code + portal password."""
    if request.method == 'POST':
        driver_code = request.POST.get('driver_code', '').strip()
        password = request.POST.get('password', '')

        try:
            driver = Driver.objects.get(driver_code=driver_code, is_portal_enabled=True)
        except Driver.DoesNotExist:
            messages.error(request, 'Invalid driver code or portal not enabled.')
            return render(request, 'driver_portal/login.html')

        if driver.check_portal_password(password):
            request.session['driver_id'] = driver.id
            driver.last_login = timezone.now()
            driver.save()
            messages.success(request, f'Welcome, {driver.name}!')
            return redirect('driver_dashboard')
        else:
            messages.error(request, 'Invalid password.')
            return render(request, 'driver_portal/login.html')

    return render(request, 'driver_portal/login.html')


def logout(request):
    """Log the driver out."""
    request.session.pop('driver_id', None)
    messages.info(request, 'You have been logged out.')
    return redirect('driver_login')


def get_current_driver(request):
    """Helper to retrieve the logged-in driver from session."""
    driver_id = request.session.get('driver_id')
    if not driver_id:
        return None
    try:
        return Driver.objects.get(id=driver_id, is_portal_enabled=True)
    except Driver.DoesNotExist:
        return None


def driver_login_required(view_func):
    """Decorator: redirect to driver login if not authenticated."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        driver = get_current_driver(request)
        if not driver:
            return redirect('driver_login')
        request.driver = driver
        return view_func(request, *args, **kwargs)
    return wrapper


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@driver_login_required
def dashboard(request):
    """Driver dashboard showing vehicle, model, recent settlements, quick actions."""
    driver = request.driver
    settings = SystemSettings.get_settings()

    # Recent settlements (last 5)
    recent = driver.settlements.all().order_by('-date')[:5]

    # Pending approval count
    pending_count = driver.settlements.filter(status='submitted').count()

    # Debt balance (for quota model)
    debt_balance = driver.debt_balance

    # ---- Monthly aggregates (new) ----
    today = date.today()
    month_start = today.replace(day=1)
    month_settlements = driver.settlements.filter(
        status='approved',
        date__gte=month_start,
        date__lte=today
    )
    month_income = month_settlements.aggregate(total=Sum('total_income'))['total'] or 0
    month_pay = month_settlements.aggregate(total=Sum('driver_pay'))['total'] or 0
    month_expenses = month_settlements.aggregate(total=Sum('total_expenses'))['total'] or 0

    # Contract progress (for contract model)
    contract_progress = None
    if driver.vehicle and driver.vehicle.operating_model == 'contract':
        month_settlements_contract = driver.settlements.filter(
            status='approved', operating_model='contract',
            date__year=today.year, date__month=today.month
        )
        monthly_gross = sum(s.total_income for s in month_settlements_contract)
        target = driver.effective_contract_target
        progress = (monthly_gross / target * 100) if target > 0 else 0
        _, days_in_month = calendar.monthrange(today.year, today.month)
        days_remaining = days_in_month - today.day
        contract_progress = {
            'target': target,
            'monthly_gross': monthly_gross,
            'progress': round(progress, 1),
            'days_remaining': days_remaining,
        }

    context = {
        'driver': driver,
        'settings': settings,
        'recent_settlements': recent,
        'pending_count': pending_count,
        'debt_balance': debt_balance,
        'contract_progress': contract_progress,
        'month_income': month_income,         # new
        'month_pay': month_pay,               # new
        'month_expenses': month_expenses,     # new
    }
    return render(request, 'driver_portal/dashboard.html', context)


# ------------------------------------------------------------------
# Settlements
# ------------------------------------------------------------------
@driver_login_required
def settlements(request):
    """List all settlements for the logged-in driver."""
    driver = request.driver
    settlements = driver.settlements.all().order_by('-date')
    return render(request, 'driver_portal/settlements.html', {
        'driver': driver,
        'settlements': settlements,
    })


@driver_login_required
def settlement_create(request):
    """Create a new settlement (daily or weekly)."""
    driver = request.driver

    if request.method == 'POST':
        form = DailySettlementForm(request.POST, request.FILES, driver=driver)
        if form.is_valid():
            settlement = form.save(commit=False)
            settlement.driver = driver
            settlement.vehicle = driver.vehicle
            settlement.operating_model = driver.vehicle.operating_model if driver.vehicle else 'quota'
            settlement.status = 'submitted'
            settlement.submitted_at = timezone.now()
            settlement.save()
            messages.success(request, 'Settlement submitted for approval.')
            return redirect('driver_settlements')
    else:
        form = DailySettlementForm(driver=driver)

    return render(request, 'driver_portal/settlement_form.html', {
        'driver': driver,
        'form': form,
    })


@driver_login_required
def settlement_view(request, settlement_id):
    """View a settlement's details."""
    driver = request.driver
    settlement = get_object_or_404(DailySettlement, id=settlement_id, driver=driver)
    return render(request, 'driver_portal/settlement_view.html', {
        'driver': driver,
        'settlement': settlement,
    })


@driver_login_required
def settlement_edit(request, settlement_id):
    """Edit a settlement (only if draft or rejected)."""
    driver = request.driver
    settlement = get_object_or_404(DailySettlement, id=settlement_id, driver=driver)

    if settlement.status not in ('draft', 'rejected'):
        messages.error(request, 'Only draft or rejected settlements can be edited.')
        return redirect('driver_settlement_view', settlement_id=settlement.id)

    if request.method == 'POST':
        form = DailySettlementForm(request.POST, request.FILES, instance=settlement, driver=driver)
        if form.is_valid():
            settlement = form.save(commit=False)
            settlement.status = 'submitted'
            settlement.submitted_at = timezone.now()
            settlement.save()
            messages.success(request, 'Settlement resubmitted for approval.')
            return redirect('driver_settlements')
    else:
        form = DailySettlementForm(instance=settlement, driver=driver)

    return render(request, 'driver_portal/settlement_form.html', {
        'driver': driver,
        'form': form,
        'edit_mode': True,
        'settlement': settlement,
    })


@driver_login_required
def settlement_print(request, settlement_id):
    driver = request.driver
    settlement = get_object_or_404(DailySettlement, id=settlement_id, driver=driver)
    settings = SystemSettings.get_settings()  # add this line
    return render(request, 'driver_portal/settlement_print.html', {
        'driver': driver,
        'settlement': settlement,
        'settings': settings,  # add this
    })


# ------------------------------------------------------------------
# Contract & Debt
# ------------------------------------------------------------------
@driver_login_required
def contract(request):
    """Contract progress dashboard for contract-model drivers."""
    driver = request.driver

    if not driver.vehicle or driver.vehicle.operating_model != 'contract':
        messages.info(request, 'You are not on a contract operating model.')
        return redirect('driver_dashboard')

    today = date.today()
    month_start = today.replace(day=1)

    monthly_settlements = driver.settlements.filter(
        status='approved', operating_model='contract',
        date__gte=month_start, date__lte=today
    ).order_by('date')

    monthly_gross = sum(s.total_income for s in monthly_settlements)
    target = driver.effective_contract_target
    progress = (monthly_gross / target * 100) if target > 0 else 0
    _, days_in_month = calendar.monthrange(today.year, today.month)
    days_remaining = days_in_month - today.day
    daily_needed = max(0, (target - monthly_gross) / max(1, days_remaining)) if days_remaining > 0 else 0

    context = {
        'driver': driver,
        'target': target,
        'monthly_gross': monthly_gross,
        'remaining': max(0, target - monthly_gross),
        'progress': round(progress, 1),
        'days_remaining': days_remaining,
        'daily_average_needed': daily_needed,
        'settlements': monthly_settlements,
    }
    return render(request, 'driver_portal/contract.html', context)


@driver_login_required
def debt(request):
    """Debt ledger for quota-model drivers."""
    driver = request.driver

    if not driver.vehicle or driver.vehicle.operating_model != 'quota':
        messages.info(request, 'You are not on a quota operating model.')
        return redirect('driver_dashboard')

    settlements = driver.settlements.filter(
        status='approved', operating_model='quota'
    ).order_by('-date')

    context = {
        'driver': driver,
        'settlements': settlements,
        'current_debt': driver.debt_balance,
    }
    return render(request, 'driver_portal/debt.html', context)


# ------------------------------------------------------------------
# Profile
# ------------------------------------------------------------------
@driver_login_required
def profile(request):
    """Driver profile view."""
    driver = request.driver
    return render(request, 'driver_portal/profile.html', {'driver': driver})


@driver_login_required
def change_password(request):
    """Allow driver to change their portal password."""
    driver = request.driver

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validate current password
        if not driver.check_portal_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'driver_portal/change_password.html')

        # Validate new password
        if len(new_password) < 4:
            messages.error(request, 'New password must be at least 4 characters.')
            return render(request, 'driver_portal/change_password.html')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'driver_portal/change_password.html')

        # Update password
        driver.set_portal_password(new_password)
        driver.save()
        messages.success(request, 'Password changed successfully.')
        return redirect('driver_profile')

    return render(request, 'driver_portal/change_password.html')
