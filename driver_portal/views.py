from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
import calendar

from drivers.models import Driver
from settlements.models import DailySettlement
from settlements.forms import DriverSettlementForm
from accounts.models import SystemSettings


def _get_driver(request):
    """Return the logged-in driver or redirect to login."""
    driver_id = request.session.get('driver_id')
    if not driver_id:
        return None
    return get_object_or_404(Driver, id=driver_id)


def login(request):
    if request.method == 'POST':
        driver_code = request.POST.get('driver_code')
        password = request.POST.get('password')

        try:
            driver = Driver.objects.get(driver_code=driver_code, is_portal_enabled=True)
            if check_password(password, driver.portal_password):
                request.session['driver_id'] = driver.id
                request.session['driver_name'] = driver.name
                driver.last_login = timezone.now()
                driver.save()
                return redirect('driver_dashboard')
            else:
                messages.error(request, 'Invalid password')
        except Driver.DoesNotExist:
            messages.error(request, 'Driver not found or portal not enabled')

    return render(request, 'driver_portal/login.html')


def logout(request):
    request.session.flush()
    return redirect('driver_login')


def dashboard(request):
    driver = _get_driver(request)
    if not driver:
        return redirect('driver_login')

    today = date.today()
    month_start = today.replace(day=1)

    # Recent settlements
    recent_settlements = DailySettlement.objects.filter(driver=driver).order_by('-date', '-id')[:10]

    # Monthly summary (approved only for financials)
    monthly_settlements = DailySettlement.objects.filter(
        driver=driver, date__gte=month_start, date__lte=today, status='approved'
    )
    monthly_income = sum(s.total_income for s in monthly_settlements)
    monthly_driver_pay = sum(s.driver_pay for s in monthly_settlements)

    # Pending settlements (submitted, awaiting approval)
    pending_count = DailySettlement.objects.filter(driver=driver, status='submitted').count()
    rejected_count = DailySettlement.objects.filter(driver=driver, status='rejected').count()
    draft_count = DailySettlement.objects.filter(driver=driver, status='draft').count()

    # Last settlement status
    last_settlement = DailySettlement.objects.filter(driver=driver).order_by('-date', '-id').first()

    # Debt balance (for quota system)
    debt_balance = driver.debt_balance

    # Contract progress (for contract system)
    contract_progress = 0
    contract_target = 0
    contract_monthly_gross = 0
    contract_remaining = 0
    if driver.vehicle and driver.vehicle.operating_model == 'contract':
        contract_settlements = DailySettlement.objects.filter(
            driver=driver, date__gte=month_start, date__lte=today,
            operating_model='contract', status='approved'
        )
        contract_monthly_gross = sum(s.total_income for s in contract_settlements)
        contract_target = driver.effective_contract_target
        contract_remaining = max(0, contract_target - contract_monthly_gross)
        contract_progress = min(100, (contract_monthly_gross / contract_target * 100)) if contract_target > 0 else 0

    context = {
        'driver': driver,
        'recent_settlements': recent_settlements,
        'monthly_income': monthly_income,
        'monthly_driver_pay': monthly_driver_pay,
        'debt_balance': debt_balance,
        'contract_progress': contract_progress,
        'contract_target': contract_target,
        'contract_monthly_gross': contract_monthly_gross,
        'contract_remaining': contract_remaining,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'draft_count': draft_count,
        'last_settlement': last_settlement,
    }
    return render(request, 'driver_portal/dashboard.html', context)


def settlement_create(request):
    driver = _get_driver(request)
    if not driver:
        return redirect('driver_login')

    if not driver.vehicle:
        messages.error(request, 'You have no vehicle assigned. Contact the owner.')
        return redirect('driver_dashboard')

    # Determine default frequency
    default_freq = driver.settlement_frequency or driver.vehicle.default_settlement_frequency

    if request.method == 'POST':
        form = DriverSettlementForm(request.POST)
        if form.is_valid():
            settlement = form.save(commit=False)
            settlement.driver = driver
            settlement.vehicle = driver.vehicle

            # Check for existing settlement on the same date (unique constraint)
            existing = DailySettlement.objects.filter(
                vehicle=settlement.vehicle,
                driver=settlement.driver,
                date=settlement.date,
            ).first()

            if existing:
                if existing.status in ('draft', 'rejected'):
                    messages.info(
                        request,
                        f'A settlement for {settlement.date} already exists. '
                        f'You can edit and resubmit it.'
                    )
                    return redirect('driver_settlement_edit', settlement_id=existing.id)
                else:
                    messages.error(
                        request,
                        f'A settlement for {settlement.date} already exists '
                        f'and is {existing.get_status_display().lower()}. '
                        f'You cannot create a duplicate.'
                    )
                    return redirect('driver_settlements')

            settlement.status = 'submitted'
            settlement.submitted_at = timezone.now()
            settlement.save()
            messages.success(request, 'Settlement submitted successfully! Awaiting owner approval.')
            return redirect('driver_settlements')
    else:
        # Pre-fill date with today and default frequency
        initial = {
            'settlement_period': default_freq,
            'date': date.today().isoformat(),
        }
        # Default week: Monday to Sunday
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        initial['week_start'] = monday.isoformat()
        initial['week_end'] = sunday.isoformat()
        form = DriverSettlementForm(initial=initial)

    return render(request, 'driver_portal/settlement_form.html', {
        'driver': driver,
        'form': form,
        'is_edit': False,
    })


def settlement_edit(request, settlement_id):
    driver = _get_driver(request)
    if not driver:
        return redirect('driver_login')

    settlement = get_object_or_404(DailySettlement, id=settlement_id, driver=driver)

    # Only allow editing if draft or rejected
    if settlement.status not in ('draft', 'rejected'):
        messages.error(request, 'You can only edit settlements that are in draft or rejected status.')
        return redirect('driver_settlements')

    if request.method == 'POST':
        form = DriverSettlementForm(request.POST, instance=settlement)
        if form.is_valid():
            settlement = form.save(commit=False)
            settlement.status = 'submitted'
            settlement.submitted_at = timezone.now()
            settlement.save()
            messages.success(request, 'Settlement updated and resubmitted for approval.')
            return redirect('driver_settlements')
    else:
        form = DriverSettlementForm(instance=settlement)

    return render(request, 'driver_portal/settlement_form.html', {
        'driver': driver,
        'form': form,
        'is_edit': True,
        'settlement': settlement,
    })


def settlement_view(request, settlement_id):
    driver = _get_driver(request)
    if not driver:
        return redirect('driver_login')

    settlement = get_object_or_404(DailySettlement, id=settlement_id, driver=driver)

    return render(request, 'driver_portal/settlement_view.html', {
        'driver': driver,
        'settlement': settlement,
    })


def settlement_print(request, settlement_id):
    driver = _get_driver(request)
    if not driver:
        return redirect('driver_login')

    settlement = get_object_or_404(DailySettlement, id=settlement_id, driver=driver)

    try:
        settings = SystemSettings.objects.first()
    except SystemSettings.DoesNotExist:
        settings = None

    return render(request, 'driver_portal/settlement_print.html', {
        'driver': driver,
        'settlement': settlement,
        'settings': settings,
    })


def settlements(request):
    driver = _get_driver(request)
    if not driver:
        return redirect('driver_login')

    # Filter by status and date if provided
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    all_settlements = DailySettlement.objects.filter(driver=driver).order_by('-date', '-id')

    if status_filter:
        all_settlements = all_settlements.filter(status=status_filter)
    if date_from:
        all_settlements = all_settlements.filter(date__gte=date_from)
    if date_to:
        all_settlements = all_settlements.filter(date__lte=date_to)

    # Summary counts
    status_counts = {
        'draft': DailySettlement.objects.filter(driver=driver, status='draft').count(),
        'submitted': DailySettlement.objects.filter(driver=driver, status='submitted').count(),
        'approved': DailySettlement.objects.filter(driver=driver, status='approved').count(),
        'rejected': DailySettlement.objects.filter(driver=driver, status='rejected').count(),
    }

    return render(request, 'driver_portal/settlements.html', {
        'driver': driver,
        'settlements': all_settlements,
        'status_counts': status_counts,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


def contract(request):
    driver = _get_driver(request)
    if not driver:
        return redirect('driver_login')

    if not driver.vehicle or driver.vehicle.operating_model != 'contract':
        messages.error(request, 'You are not on the contract system')
        return redirect('driver_dashboard')

    today = date.today()
    month_start = today.replace(day=1)

    settlements = DailySettlement.objects.filter(
        driver=driver, date__gte=month_start, date__lte=today,
        operating_model='contract', status='approved'
    ).order_by('date')

    monthly_gross = sum(s.total_income for s in settlements)
    target = driver.effective_contract_target
    remaining = max(0, target - monthly_gross)
    progress = min(100, (monthly_gross / target * 100)) if target > 0 else 0

    _, days_in_month = calendar.monthrange(today.year, today.month)
    days_remaining = days_in_month - today.day
    days_passed = today.day

    daily_average_needed = remaining / days_remaining if days_remaining > 0 else 0
    daily_average_current = monthly_gross / days_passed if days_passed > 0 else 0

    # Calculate payouts
    if monthly_gross >= target:
        is_success = True
        bonus_type = driver.vehicle.contract_success_bonus_type
        if bonus_type == 'fixed':
            success_bonus = driver.effective_contract_success_bonus_fixed
        elif bonus_type == 'percentage':
            success_bonus = (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
        else:
            success_bonus = driver.effective_contract_success_bonus_fixed + \
                (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
        success_pay = success_bonus
        failure_pay = 0
    else:
        is_success = False
        failure_pct = driver.effective_contract_failure_percentage
        success_bonus = 0
        success_pay = 0
        failure_pay = (failure_pct / 100) * monthly_gross

    context = {
        'driver': driver,
        'daily_settlements': settlements,
        'monthly_gross': monthly_gross,
        'target': target,
        'remaining': remaining,
        'progress': progress,
        'days_remaining': days_remaining,
        'days_passed': days_passed,
        'daily_average_needed': daily_average_needed,
        'daily_average_current': daily_average_current,
        'is_success': is_success,
        'success_bonus': success_bonus,
        'success_pay': success_pay,
        'failure_pay': failure_pay,
        'failure_percentage': driver.effective_contract_failure_percentage,
        'month_name': today.strftime('%B'),
        'year': today.year,
    }
    return render(request, 'driver_portal/contract.html', context)


def profile(request):
    driver = _get_driver(request)
    if not driver:
        return redirect('driver_login')

    return render(request, 'driver_portal/profile.html', {'driver': driver})