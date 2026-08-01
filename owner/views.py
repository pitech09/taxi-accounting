"""
Owner portal views.
All views require staff authentication (owner access).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import date, datetime, timedelta
import calendar
from decimal import Decimal

from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from cashbook.models import CashInHand, BankAccount, CashTransaction
from accounts.models import SystemSettings
from contracts.models import MonthlyContractSummary
from settlements.forms import SettlementApprovalForm
from loans.models import Loan


def _to_decimal(value, default=Decimal('0.00')):
    """Safely convert a POST string value to Decimal."""
    if value is None or value == '':
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


def is_owner(user):
    """Check if user is an owner (staff)."""
    return user.is_authenticated and user.is_staff


owner_required = user_passes_test(is_owner, login_url='/accounts/login/')


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------
@owner_required
def dashboard(request):
    """Owner dashboard with summary cards and pending approvals."""
    settings = SystemSettings.get_settings()
    cash_balance = CashInHand.get_balance()
    bank_total = BankAccount.objects.filter(is_active=True).aggregate(
        total=Sum('current_balance')
    )['total'] or 0

    pending_count = DailySettlement.objects.filter(status='submitted').count()
    approved_today = DailySettlement.objects.filter(
        status='approved', approved_at__date=date.today()
    ).count()

    # Recent settlements
    recent_settlements = DailySettlement.objects.filter(
        status='approved'
    ).order_by('-approved_at')[:5]

    # Monthly summary
    today = date.today()
    month_start = today.replace(day=1)
    monthly_data = DailySettlement.objects.filter(
        status='approved', date__gte=month_start, date__lte=today
    ).aggregate(
        total_income=Sum('total_income'),
        total_owner=Sum('total_owner_collected'),
        total_driver=Sum('driver_pay'),
    )

    # Loan summary
    total_driver_loans = Loan.objects.filter(
        loan_type='driver', status='active'
    ).aggregate(total=Sum('outstanding_balance'))['total'] or 0

    total_business_loans = Loan.objects.filter(
        loan_type='business', status='active'
    ).aggregate(total=Sum('outstanding_balance'))['total'] or 0

    context = {
        'settings': settings,
        'cash_balance': cash_balance,
        'bank_total': bank_total,
        'pending_count': pending_count,
        'approved_today': approved_today,
        'recent_settlements': recent_settlements,
        'monthly_income': monthly_data['total_income'] or 0,
        'monthly_owner': monthly_data['total_owner'] or 0,
        'monthly_driver': monthly_data['total_driver'] or 0,
        'total_driver_loans': total_driver_loans,
        'total_business_loans': total_business_loans,
        'today': today,  # <-- ADDED
    }
    return render(request, 'owner/dashboard.html', context)


# ------------------------------------------------------------------
# Vehicle CRUD
# ------------------------------------------------------------------
@owner_required
def vehicle_list(request):
    vehicles = Vehicle.objects.all().order_by('name')
    return render(request, 'owner/vehicles/list.html', {'vehicles': vehicles})


@owner_required
def vehicle_add(request):
    if request.method == 'POST':
        vehicle = Vehicle(
            name=request.POST.get('name'),
            vehicle_type=request.POST.get('vehicle_type'),
            seats=request.POST.get('seats'),
            plate=request.POST.get('plate'),
            operating_model=request.POST.get('operating_model', 'quota'),
            daily_quota=request.POST.get('daily_quota', 250),
            monthly_salary=request.POST.get('monthly_salary', 3000),
            driver_percentage=request.POST.get('driver_percentage', 30),
            contract_target=request.POST.get('contract_target', 15000),
            contract_success_bonus_type=request.POST.get('contract_success_bonus_type', 'fixed'),
            contract_success_bonus_fixed=request.POST.get('contract_success_bonus_fixed', 2000),
            contract_success_bonus_percentage=request.POST.get('contract_success_bonus_percentage', 10),
            contract_failure_percentage=request.POST.get('contract_failure_percentage', 20),
            insurance=request.POST.get('insurance', 0),
            permit_cost=request.POST.get('permit_cost', 0),
            loan_payment=request.POST.get('loan_payment', 0),
            default_settlement_frequency=request.POST.get('default_settlement_frequency', 'daily'),
            is_active=request.POST.get('is_active') == 'on',
        )
        vehicle.save()
        messages.success(request, 'Vehicle added successfully.')
        return redirect('owner_vehicle_list')
    return render(request, 'owner/vehicles/add.html', {'vehicle': Vehicle()})


@owner_required
def vehicle_edit(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    if request.method == 'POST':
        vehicle.name = request.POST.get('name')
        vehicle.vehicle_type = request.POST.get('vehicle_type')
        vehicle.seats = request.POST.get('seats')
        vehicle.plate = request.POST.get('plate')
        vehicle.operating_model = request.POST.get('operating_model', 'quota')
        vehicle.daily_quota = request.POST.get('daily_quota', 250)
        vehicle.monthly_salary = request.POST.get('monthly_salary', 3000)
        vehicle.driver_percentage = request.POST.get('driver_percentage', 30)
        vehicle.contract_target = request.POST.get('contract_target', 15000)
        vehicle.contract_success_bonus_type = request.POST.get('contract_success_bonus_type', 'fixed')
        vehicle.contract_success_bonus_fixed = request.POST.get('contract_success_bonus_fixed', 2000)
        vehicle.contract_success_bonus_percentage = request.POST.get('contract_success_bonus_percentage', 10)
        vehicle.contract_failure_percentage = request.POST.get('contract_failure_percentage', 20)
        vehicle.insurance = request.POST.get('insurance', 0)
        vehicle.permit_cost = request.POST.get('permit_cost', 0)
        vehicle.loan_payment = request.POST.get('loan_payment', 0)
        vehicle.default_settlement_frequency = request.POST.get('default_settlement_frequency', 'daily')
        vehicle.is_active = request.POST.get('is_active') == 'on'
        vehicle.save()
        messages.success(request, 'Vehicle updated successfully.')
        return redirect('owner_vehicle_list')
    return render(request, 'owner/vehicles/edit.html', {'vehicle': vehicle})


# ------------------------------------------------------------------
# Driver CRUD
# ------------------------------------------------------------------
@owner_required
def driver_list(request):
    drivers = Driver.objects.all().order_by('name')
    return render(request, 'owner/drivers/list.html', {'drivers': drivers})


@owner_required
def driver_add(request):
    if request.method == 'POST':
        driver = Driver(
            name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email') or None,
            address=request.POST.get('address', ''),
            id_number=request.POST.get('id_number', ''),
            license_type=request.POST.get('license_type', ''),
            license_number=request.POST.get('license_number', ''),
            license_expiry=request.POST.get('license_expiry') or None,
            vehicle_id=request.POST.get('vehicle') or None,
            settlement_frequency=request.POST.get('settlement_frequency') or None,
            is_portal_enabled=request.POST.get('is_portal_enabled') == 'on',
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
        # Handle portal password
        portal_password = request.POST.get('portal_password')
        if portal_password:
            driver.set_portal_password(portal_password)
        else:
            driver.portal_password = None
        driver.save()
        messages.success(request, f'Driver {driver.name} added successfully.')
        return redirect('owner_driver_list')
    vehicles = Vehicle.objects.filter(is_active=True)
    return render(request, 'owner/drivers/add.html', {'vehicles': vehicles})


@owner_required
def driver_edit(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    if request.method == 'POST':
        driver.name = request.POST.get('name')
        driver.phone = request.POST.get('phone')
        driver.email = request.POST.get('email') or None
        driver.address = request.POST.get('address', '')
        driver.id_number = request.POST.get('id_number', '')
        driver.license_type = request.POST.get('license_type', '')
        driver.license_number = request.POST.get('license_number', '')
        driver.license_expiry = request.POST.get('license_expiry') or None
        driver.vehicle_id = request.POST.get('vehicle') or None
        driver.settlement_frequency = request.POST.get('settlement_frequency') or None
        driver.is_portal_enabled = request.POST.get('is_portal_enabled') == 'on'
        driver.is_active = request.POST.get('is_active') == 'on'

        # Handle portal password
        portal_password = request.POST.get('portal_password')
        if portal_password:
            driver.set_portal_password(portal_password)
        driver.save()
        messages.success(request, f'Driver {driver.name} updated successfully.')
        return redirect('owner_driver_list')
    vehicles = Vehicle.objects.filter(is_active=True)
    return render(request, 'owner/drivers/edit.html', {'driver': driver, 'vehicles': vehicles})


@owner_required
def driver_settlements(request, driver_id):
    """List all settlements for a specific driver."""
    driver = get_object_or_404(Driver, id=driver_id)
    settlements = driver.settlements.all().order_by('-date')
    return render(request, 'owner/drivers/settlements.html', {'driver': driver, 'settlements': settlements})


# ------------------------------------------------------------------
# Settlements
# ------------------------------------------------------------------
@owner_required
def settlement_list(request):
    settlements = DailySettlement.objects.all().order_by('-date')
    # Filters
    status = request.GET.get('status')
    if status:
        settlements = settlements.filter(status=status)
    vehicle_id = request.GET.get('vehicle')
    if vehicle_id:
        settlements = settlements.filter(vehicle_id=vehicle_id)
    driver_id = request.GET.get('driver')
    if driver_id:
        settlements = settlements.filter(driver_id=driver_id)
    return render(request, 'owner/settlements/list.html', {
        'settlements': settlements,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'drivers': Driver.objects.filter(is_active=True),
    })


@owner_required
def settlement_add(request):
    if request.method == 'POST':
        settlement = DailySettlement(
            driver_id=request.POST.get('driver'),
            vehicle_id=request.POST.get('vehicle'),
            date=request.POST.get('date'),
            settlement_period=request.POST.get('settlement_period', 'daily'),
            week_start=request.POST.get('week_start') or None,
            week_end=request.POST.get('week_end') or None,
            cash_collected=_to_decimal(request.POST.get('cash_collected')),
            mobile_collected=_to_decimal(request.POST.get('mobile_collected')),
            card_collected=_to_decimal(request.POST.get('card_collected')),
            fuel_expense=_to_decimal(request.POST.get('fuel_expense')),
            maintenance_expense=_to_decimal(request.POST.get('maintenance_expense')),
            toll_expense=_to_decimal(request.POST.get('toll_expense')),
            other_expense=_to_decimal(request.POST.get('other_expense')),
            other_expense_desc=request.POST.get('other_expense_desc', ''),
            driver_notes=request.POST.get('driver_notes', ''),
            status='approved',
        )
        settlement.save()
        messages.success(request, 'Settlement added and approved successfully.')
        return redirect('owner_settlement_list')
    return render(request, 'owner/settlements/add.html', {
        'vehicles': Vehicle.objects.filter(is_active=True),
        'drivers': Driver.objects.filter(is_active=True),
    })


@owner_required
def settlement_detail(request, settlement_id):
    settlement = get_object_or_404(DailySettlement, id=settlement_id)
    return render(request, 'owner/settlements/detail.html', {'settlement': settlement})


@owner_required
def settlement_edit(request, settlement_id):
    settlement = get_object_or_404(DailySettlement, id=settlement_id)
    if request.method == 'POST':
        settlement.driver_id = request.POST.get('driver')
        settlement.vehicle_id = request.POST.get('vehicle')
        settlement.date = request.POST.get('date')
        settlement.settlement_period = request.POST.get('settlement_period', 'daily')
        settlement.week_start = request.POST.get('week_start') or None
        settlement.week_end = request.POST.get('week_end') or None
        settlement.cash_collected = _to_decimal(request.POST.get('cash_collected'))
        settlement.mobile_collected = _to_decimal(request.POST.get('mobile_collected'))
        settlement.card_collected = _to_decimal(request.POST.get('card_collected'))
        settlement.fuel_expense = _to_decimal(request.POST.get('fuel_expense'))
        settlement.maintenance_expense = _to_decimal(request.POST.get('maintenance_expense'))
        settlement.toll_expense = _to_decimal(request.POST.get('toll_expense'))
        settlement.other_expense = _to_decimal(request.POST.get('other_expense'))
        settlement.other_expense_desc = request.POST.get('other_expense_desc', '')
        settlement.driver_notes = request.POST.get('driver_notes', '')
        settlement.save()
        messages.success(request, 'Settlement updated successfully.')
        return redirect('owner_settlement_detail', settlement_id=settlement.id)
    return render(request, 'owner/settlements/edit.html', {
        'settlement': settlement,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'drivers': Driver.objects.filter(is_active=True),
    })


@owner_required
def settlement_delete(request, settlement_id):
    settlement = get_object_or_404(DailySettlement, id=settlement_id)
    if request.method == 'POST':
        settlement.delete()
        messages.success(request, 'Settlement deleted.')
        return redirect('owner_settlement_list')
    return render(request, 'owner/settlements/delete.html', {'settlement': settlement})


@owner_required
def settlement_export_csv(request):
    import csv
    from django.http import HttpResponse
    settlements = DailySettlement.objects.all().order_by('-date')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="settlements.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Driver', 'Vehicle', 'Model', 'Income', 'Expenses',
                     'Gross Profit', 'Driver Pay', 'Owner Collection', 'Status'])
    for s in settlements:
        writer.writerow([
            s.date, s.driver.name, s.vehicle.name, s.operating_model,
            s.total_income, s.total_expenses, s.gross_profit,
            s.driver_pay, s.total_owner_collected, s.status,
        ])
    return response


# ------------------------------------------------------------------
# Approvals
# ------------------------------------------------------------------
@owner_required
def pending_approvals(request):
    # Get all submitted settlements (pending)
    settlements = DailySettlement.objects.filter(status='submitted').order_by('-submitted_at')

    # Pre-run calculations for each to preview driver_pay & owner_collection
    for s in settlements:
        s._run_calculations()   # fills in all calculated fields (no save)

    return render(request, 'owner/approvals/pending.html', {'settlements': settlements})

@owner_required
def review_settlement(request, settlement_id):
    settlement = get_object_or_404(DailySettlement, id=settlement_id)

    # Prevent re-approving
    if settlement.status == 'approved':
        messages.warning(request, 'This settlement is already approved.')
        return redirect('owner_pending_approvals')

    # ---- NEW: Run calculations to preview (does not save) ----
    settlement._run_calculations()  # Populates all driver_pay, total_owner_collected, etc.

    if request.method == 'POST':
        form = SettlementApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            owner_notes = form.cleaned_data.get('owner_notes', '')

            if action == 'approve':
                settlement.status = 'approved'
                settlement.approved_at = timezone.now()
                settlement.approved_by = request.user
                settlement.owner_notes = owner_notes
                # save() will recalculate and create cash transaction
                settlement.save()
                messages.success(
                    request,
                    f'Settlement for {settlement.driver.name} approved! '
                    f'Owner collection: M {settlement.total_owner_collected:.2f} added to cash.'
                )
            else:  # reject
                settlement.status = 'rejected'
                settlement.owner_notes = owner_notes
                settlement.save()
                messages.warning(
                    request,
                    f'Settlement for {settlement.driver.name} rejected.'
                )
            return redirect('owner_pending_approvals')
    else:
        # GET – pre-fill owner_notes
        form = SettlementApprovalForm(initial={'owner_notes': settlement.owner_notes})

    context = {
        'settlement': settlement,
        'form': form,
        'model_display': settlement.get_operating_model_display(),
    }
    return render(request, 'owner/approvals/review.html', context)
# ------------------------------------------------------------------
# Contract management
# ------------------------------------------------------------------
@owner_required
def contract_dashboard(request):
    """List all contract-model drivers with progress."""
    contract_drivers = Driver.objects.filter(
        vehicle__operating_model='contract', is_active=True
    ).select_related('vehicle')

    today = date.today()
    month_start = today.replace(day=1)

    contracts = []
    for driver in contract_drivers:
        monthly_settlements = DailySettlement.objects.filter(
            driver=driver, status='approved',
            date__year=today.year, date__month=today.month
        )
        monthly_gross = monthly_settlements.aggregate(total=Sum('total_income'))['total'] or 0
        target = driver.effective_contract_target
        progress = (monthly_gross / target * 100) if target > 0 else 0
        _, days_in_month = calendar.monthrange(today.year, today.month)
        days_remaining = days_in_month - today.day
        daily_needed = max(0, (target - monthly_gross) / max(1, days_remaining)) if days_remaining > 0 else 0

        contracts.append({
            'driver': driver,
            'target': target,
            'monthly_gross': monthly_gross,
            'remaining': max(0, target - monthly_gross),
            'progress': round(progress, 1),
            'days_remaining': days_remaining,
            'daily_average_needed': daily_needed,
            'status': 'on-track' if progress >= 100 else ('at-risk' if progress < 50 else 'progress'),
            'status_class': 'success' if progress >= 100 else ('danger' if progress < 50 else 'warning'),
        })

    return render(request, 'owner/contract/dashboard.html', {'contracts': contracts})


@owner_required
def contract_detail(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    today = date.today()
    month_start = today.replace(day=1)

    monthly_settlements = DailySettlement.objects.filter(
        driver=driver, status='approved',
        date__year=today.year, date__month=today.month
    ).order_by('date')

    monthly_gross = monthly_settlements.aggregate(total=Sum('total_income'))['total'] or 0
    target = driver.effective_contract_target
    progress = (monthly_gross / target * 100) if target > 0 else 0

    # Historical summaries
    summaries = MonthlyContractSummary.objects.filter(driver=driver).order_by('-year', '-month')

    context = {
        'driver': driver,
        'target': target,
        'monthly_gross': monthly_gross,
        'remaining': max(0, target - monthly_gross),
        'progress': round(progress, 1),
        'settlements': monthly_settlements,
        'summaries': summaries,
    }
    return render(request, 'owner/contract/detail.html', context)


@owner_required
def contract_settle(request, driver_id):
    """Finalise a contract at month end."""
    driver = get_object_or_404(Driver, id=driver_id)
    today = date.today()

    if request.method == 'POST':
        month = int(request.POST.get('month', today.month))
        year = int(request.POST.get('year', today.year))

        # Check if already settled
        if MonthlyContractSummary.objects.filter(driver=driver, year=year, month=month).exists():
            messages.warning(request, f'Contract already settled for {month}/{year}.')
            return redirect('owner_contract_detail', driver_id=driver.id)

        # Calculate monthly totals
        month_start = date(year, month, 1)
        _, days_in_month = calendar.monthrange(year, month)
        month_end = date(year, month, days_in_month)

        settlements = DailySettlement.objects.filter(
            driver=driver, status='approved',
            date__gte=month_start, date__lte=month_end,
            operating_model='contract'
        )

        if not settlements.exists():
            messages.warning(request, 'No approved settlements found for this period.')
            return redirect('owner_contract_detail', driver_id=driver.id)

        monthly_gross = settlements.aggregate(total=Sum('total_income'))['total'] or 0
        total_expenses = settlements.aggregate(total=Sum('total_expenses'))['total'] or 0
        gross_profit = monthly_gross - total_expenses
        target = driver.effective_contract_target
        is_success = monthly_gross >= target

        if is_success:
            bonus_type = driver.vehicle.contract_success_bonus_type
            if bonus_type == 'fixed':
                driver_pay = driver.effective_contract_success_bonus_fixed
            elif bonus_type == 'percentage':
                driver_pay = (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
            else:
                driver_pay = (driver.effective_contract_success_bonus_fixed +
                              (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross)
        else:
            driver_pay = (driver.effective_contract_failure_percentage / 100) * monthly_gross

        owner_pay = monthly_gross - driver_pay

        MonthlyContractSummary.objects.create(
            driver=driver,
            vehicle=driver.vehicle,
            year=year,
            month=month,
            target=target,
            total_gross=monthly_gross,
            total_expenses=total_expenses,
            gross_profit=gross_profit,
            is_success=is_success,
            bonus_type=driver.vehicle.contract_success_bonus_type if is_success else '',
            success_bonus_fixed=driver.effective_contract_success_bonus_fixed if is_success else 0,
            success_bonus_percentage=driver.effective_contract_success_bonus_percentage if is_success else 0,
            failure_percentage=driver.effective_contract_failure_percentage if not is_success else 0,
            driver_pay=driver_pay,
            owner_pay=owner_pay,
            days_worked=settlements.count(),
        )

        messages.success(request, f'Contract settled for {driver.name}: '
                         f'{"Success" if is_success else "Failed"} - '
                         f'Driver: M{driver_pay:.2f}, Owner: M{owner_pay:.2f}')
        return redirect('owner_contract_detail', driver_id=driver.id)

    return render(request, 'owner/contract/settle.html', {'driver': driver})


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------
@owner_required
def settings_view(request):
    settings = SystemSettings.get_settings()
    return render(request, 'owner/settings.html', {'settings': settings})


@owner_required
def settings_update(request):
    settings = SystemSettings.get_settings()
    if request.method == 'POST':
        settings.company_name = request.POST.get('company_name', settings.company_name)
        settings.company_phone = request.POST.get('company_phone', '')
        settings.company_email = request.POST.get('company_email', '')
        settings.company_address = request.POST.get('company_address', '')
        settings.debt_cap = request.POST.get('debt_cap', settings.debt_cap)
        settings.repayment_percentage = request.POST.get('repayment_percentage', settings.repayment_percentage)
        settings.minimum_driver_take = request.POST.get('minimum_driver_take', settings.minimum_driver_take)
        settings.days_in_month_for_salary = request.POST.get('days_in_month_for_salary', settings.days_in_month_for_salary)
        settings.contract_settlement_day = request.POST.get('contract_settlement_day', settings.contract_settlement_day)
        settings.cash_alert_threshold = request.POST.get('cash_alert_threshold', settings.cash_alert_threshold)
        settings.bank_alert_threshold = request.POST.get('bank_alert_threshold', settings.bank_alert_threshold)
        settings.default_bank_account_id = request.POST.get('default_bank_account') or None
        settings.save()
        messages.success(request, 'Settings updated successfully.')
        return redirect('owner_settings')
    return render(request, 'owner/settings.html', {
        'settings': settings,
        'bank_accounts': BankAccount.objects.filter(is_active=True),
    })