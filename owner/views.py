from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.http import HttpResponse
from datetime import date, timedelta, datetime
from decimal import Decimal
import csv
import calendar

from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from settlements.forms import OwnerApprovalForm, OwnerSettlementForm
from contracts.models import MonthlyContractSummary
from accounts.models import SystemSettings
from cashbook.models import CashInHand, CashTransaction, BankAccount
from cashbook.views import get_total_bank_balance


@login_required
@staff_member_required
def dashboard(request):
    today = date.today()
    month_start = today.replace(day=1)

    # Summary stats
    total_vehicles = Vehicle.objects.filter(is_active=True).count()
    total_drivers = Driver.objects.filter(is_active=True).count()

    # Monthly settlements (approved only for financials)
    monthly_settlements = DailySettlement.objects.filter(
        date__gte=month_start, date__lte=today, status='approved'
    )
    monthly_income = monthly_settlements.aggregate(Sum('total_income'))['total_income__sum'] or 0
    monthly_owner_collected = monthly_settlements.aggregate(Sum('total_owner_collected'))['total_owner_collected__sum'] or 0
    monthly_driver_pay = monthly_settlements.aggregate(Sum('driver_pay'))['driver_pay__sum'] or 0

    # Pending approvals count
    pending_approvals = DailySettlement.objects.filter(status='submitted').count()

    # Cash book balances
    cash_in_hand = CashInHand.get_balance()
    total_bank = get_total_bank_balance()

    # Alerts
    settings = SystemSettings.objects.first()
    alerts = []
    if settings:
        if cash_in_hand > settings.cash_alert_threshold:
            alerts.append({
                'type': 'info',
                'message': f'Cash in hand is high (M {cash_in_hand:.2f}) - consider making a bank deposit.',
            })
        if total_bank < settings.bank_alert_threshold:
            alerts.append({
                'type': 'warning',
                'message': f'Total bank balance is below M {settings.bank_alert_threshold:.2f}.',
            })

    # Model breakdown
    model_breakdown = []
    for model_key, model_name in Vehicle.OPERATING_MODELS:
        count = Vehicle.objects.filter(operating_model=model_key, is_active=True).count()
        model_income = monthly_settlements.filter(operating_model=model_key).aggregate(
            Sum('total_income'))['total_income__sum'] or 0
        model_breakdown.append({
            'name': model_name,
            'key': model_key,
            'count': count,
            'income': model_income,
        })

    # Recent settlements
    recent_settlements = DailySettlement.objects.select_related('driver', 'vehicle').order_by('-date', '-id')[:10]

    # Contract summary
    contract_drivers = Driver.objects.filter(vehicle__operating_model='contract', is_active=True)
    contracts_on_target = 0
    contracts_at_risk = 0
    contracts_achieved = 0

    for driver in contract_drivers:
        settlements = DailySettlement.objects.filter(
            driver=driver, date__gte=month_start, date__lte=today,
            operating_model='contract', status='approved'
        )
        monthly_gross = sum(s.total_income for s in settlements)
        target = driver.effective_contract_target
        progress = min(100, (monthly_gross / target * 100)) if target > 0 else 0

        if progress >= 100:
            contracts_achieved += 1
        elif progress >= 70:
            contracts_on_target += 1
        else:
            contracts_at_risk += 1

    context = {
        'total_vehicles': total_vehicles,
        'total_drivers': total_drivers,
        'monthly_income': monthly_income,
        'monthly_owner_collected': monthly_owner_collected,
        'monthly_driver_pay': monthly_driver_pay,
        'model_breakdown': model_breakdown,
        'recent_settlements': recent_settlements,
        'contracts_on_target': contracts_on_target,
        'contracts_at_risk': contracts_at_risk,
        'contracts_achieved': contracts_achieved,
        'total_contracts': contract_drivers.count(),
        'pending_approvals': pending_approvals,
        'cash_in_hand': cash_in_hand,
        'total_bank': total_bank,
        'alerts': alerts,
    }
    return render(request, 'owner/dashboard.html', context)


@login_required
@staff_member_required
def vehicle_list(request):
    vehicles = Vehicle.objects.all().order_by('name')
    return render(request, 'owner/vehicles/list.html', {'vehicles': vehicles})


@login_required
@staff_member_required
def vehicle_add(request):
    if request.method == 'POST':
        vehicle = Vehicle(
            name=request.POST['name'],
            vehicle_type=request.POST['vehicle_type'],
            seats=request.POST['seats'],
            plate=request.POST['plate'],
            operating_model=request.POST['operating_model'],
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
        )
        vehicle.save()
        return redirect('owner_vehicle_list')
    return render(request, 'owner/vehicles/add.html')


@login_required
@staff_member_required
def vehicle_edit(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    if request.method == 'POST':
        vehicle.name = request.POST['name']
        vehicle.vehicle_type = request.POST['vehicle_type']
        vehicle.seats = request.POST['seats']
        vehicle.plate = request.POST['plate']
        vehicle.operating_model = request.POST['operating_model']
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
        return redirect('owner_vehicle_list')
    return render(request, 'owner/vehicles/edit.html', {'vehicle': vehicle})


@login_required
@staff_member_required
def driver_list(request):
    drivers = Driver.objects.all().order_by('name')
    return render(request, 'owner/drivers/list.html', {'drivers': drivers})


@login_required
@staff_member_required
def driver_add(request):
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')
        vehicle = Vehicle.objects.get(id=vehicle_id) if vehicle_id else None
        driver = Driver(
            name=request.POST['name'],
            phone=request.POST['phone'],
            email=request.POST.get('email', ''),
            address=request.POST.get('address', ''),
            id_number=request.POST.get('id_number', ''),
            license_type=request.POST.get('license_type', ''),
            license_number=request.POST.get('license_number', ''),
            vehicle=vehicle,
            settlement_frequency=request.POST.get('settlement_frequency') or None,
            is_portal_enabled=request.POST.get('is_portal_enabled') == 'on',
            driver_code=request.POST.get('driver_code') or None,
        )
        if request.POST.get('portal_password'):
            from django.contrib.auth.hashers import make_password
            driver.portal_password = make_password(request.POST['portal_password'])
        driver.save()
        return redirect('owner_driver_list')
    vehicles = Vehicle.objects.filter(is_active=True)
    return render(request, 'owner/drivers/add.html', {'vehicles': vehicles})


@login_required
@staff_member_required
def driver_edit(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')
        driver.name = request.POST['name']
        driver.phone = request.POST['phone']
        driver.email = request.POST.get('email', '')
        driver.address = request.POST.get('address', '')
        driver.id_number = request.POST.get('id_number', '')
        driver.license_type = request.POST.get('license_type', '')
        driver.license_number = request.POST.get('license_number', '')
        driver.vehicle = Vehicle.objects.get(id=vehicle_id) if vehicle_id else None
        driver.settlement_frequency = request.POST.get('settlement_frequency') or None
        driver.is_active = request.POST.get('is_active') == 'on'
        driver.is_portal_enabled = request.POST.get('is_portal_enabled') == 'on'
        new_code = request.POST.get('driver_code', '').strip()
        if new_code:
            driver.driver_code = new_code
        if request.POST.get('portal_password'):
            from django.contrib.auth.hashers import make_password
            driver.portal_password = make_password(request.POST['portal_password'])
        driver.save()
        return redirect('owner_driver_list')
    vehicles = Vehicle.objects.filter(is_active=True)
    return render(request, 'owner/drivers/edit.html', {'driver': driver, 'vehicles': vehicles})


@login_required
@staff_member_required
def settlement_list(request):
    settlements = DailySettlement.objects.select_related('driver', 'vehicle').all().order_by('-date', '-id')

    status_filter = request.GET.get('status', '')
    vehicle_filter = request.GET.get('vehicle', '')
    driver_filter = request.GET.get('driver', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if status_filter:
        settlements = settlements.filter(status=status_filter)
    if vehicle_filter:
        settlements = settlements.filter(vehicle_id=vehicle_filter)
    if driver_filter:
        settlements = settlements.filter(driver_id=driver_filter)
    if date_from:
        settlements = settlements.filter(date__gte=date_from)
    if date_to:
        settlements = settlements.filter(date__lte=date_to)

    vehicles = Vehicle.objects.all()
    drivers = Driver.objects.all()

    return render(request, 'owner/settlements/list.html', {
        'settlements': settlements,
        'vehicles': vehicles,
        'drivers': drivers,
        'status_filter': status_filter,
        'vehicle_filter': vehicle_filter,
        'driver_filter': driver_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
@staff_member_required
def settlement_add(request):
    if request.method == 'POST':
        driver_id = request.POST['driver']
        driver = get_object_or_404(Driver, id=driver_id)
        vehicle = driver.vehicle
        settlement_date = request.POST.get('date') or date.today()

        existing = DailySettlement.objects.filter(
            vehicle=vehicle, driver=driver, date=settlement_date
        ).first()
        if existing:
            messages.error(request, f'A settlement for {driver.name} on {settlement_date} already exists.')
            drivers = Driver.objects.filter(is_active=True, vehicle__isnull=False).select_related('vehicle')
            return render(request, 'owner/settlements/add.html', {'drivers': drivers})

        def _num(key):
            val = request.POST.get(key, 0)
            return val if val not in ('', None) else 0

        settlement = DailySettlement(
            vehicle=vehicle, driver=driver, date=settlement_date,
            settlement_period=request.POST.get('settlement_period', 'daily'),
            cash_collected=_num('cash_collected'), mobile_collected=_num('mobile_collected'),
            card_collected=_num('card_collected'), advance_income=_num('advance_income'),
            other_income=_num('other_income'), fuel_cost=_num('fuel_cost'),
            toll_cost=_num('toll_cost'), border_fee=_num('border_fee'),
            repair_cost=_num('repair_cost'), driver_allowance=_num('driver_allowance'),
            other_expenses=_num('other_expenses'), payment_method=request.POST.get('payment_method', 'mixed'),
            notes=request.POST.get('notes', ''), status='approved',
            approved_at=timezone.now(), approved_by=request.user,
        )
        settlement.save()
        messages.success(request, f'Settlement for {driver.name} on {settlement_date} created and approved.')
        return redirect('owner_settlement_list')

    drivers = Driver.objects.filter(is_active=True, vehicle__isnull=False).select_related('vehicle')
    return render(request, 'owner/settlements/add.html', {'drivers': drivers})


@login_required
@staff_member_required
def settlement_detail(request, settlement_id):
    settlement = get_object_or_404(DailySettlement.objects.select_related('driver', 'vehicle'), id=settlement_id)
    return render(request, 'owner/settlements/detail.html', {'settlement': settlement})


@login_required
@staff_member_required
def settlement_edit(request, settlement_id):
    settlement = get_object_or_404(DailySettlement, id=settlement_id)
    if request.method == 'POST':
        form = OwnerSettlementForm(request.POST, instance=settlement)
        if form.is_valid():
            settlement = form.save(commit=False)
            if settlement.status == 'approved':
                settlement.approved_by = request.user
                settlement.approved_at = timezone.now()
            settlement.save()
            messages.success(request, 'Settlement updated successfully.')
            return redirect('owner_settlement_detail', settlement_id=settlement.id)
    else:
        form = OwnerSettlementForm(instance=settlement)
    return render(request, 'owner/settlements/edit.html', {'form': form, 'settlement': settlement})


@login_required
@staff_member_required
def settlement_delete(request, settlement_id):
    settlement = get_object_or_404(DailySettlement, id=settlement_id)
    if request.method == 'POST':
        settlement.delete()
        messages.success(request, 'Settlement deleted successfully.')
        return redirect('owner_settlement_list')
    return render(request, 'owner/settlements/delete.html', {'settlement': settlement})


@login_required
@staff_member_required
def settlement_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="settlements.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Driver', 'Vehicle', 'Model', 'Period', 'Status',
                     'Cash', 'Mobile', 'Card', 'Advance', 'Other Income', 'Total Income',
                     'Fuel', 'Toll', 'Border', 'Repairs', 'Allowance', 'Other Expenses', 'Total Expenses',
                     'Gross Profit', 'Driver Pay', 'Owner Collected', 'Debt Status',
                     'Driver Notes', 'Owner Notes'])
    settlements = DailySettlement.objects.select_related('driver', 'vehicle').all().order_by('-date', '-id')
    status_filter = request.GET.get('status', '')
    if status_filter:
        settlements = settlements.filter(status=status_filter)
    for s in settlements:
        writer.writerow([s.date, s.driver.name, s.vehicle.name, s.operating_model,
                         s.settlement_period, s.status, s.cash_collected, s.mobile_collected,
                         s.card_collected, s.advance_income, s.other_income, s.total_income,
                         s.fuel_cost, s.toll_cost, s.border_fee, s.repair_cost,
                         s.driver_allowance, s.other_expenses, s.total_expenses,
                         s.gross_profit, s.driver_pay, s.total_owner_collected, s.debt_status,
                         s.driver_notes, s.owner_notes])
    return response


@login_required
@staff_member_required
def pending_approvals(request):
    settlements = DailySettlement.objects.filter(status='submitted').select_related('driver', 'vehicle').order_by('-submitted_at', '-date', '-id')
    vehicle_filter = request.GET.get('vehicle', '')
    driver_filter = request.GET.get('driver', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if vehicle_filter:
        settlements = settlements.filter(vehicle_id=vehicle_filter)
    if driver_filter:
        settlements = settlements.filter(driver_id=driver_filter)
    if date_from:
        settlements = settlements.filter(date__gte=date_from)
    if date_to:
        settlements = settlements.filter(date__lte=date_to)
    vehicles = Vehicle.objects.all()
    drivers = Driver.objects.all()
    return render(request, 'owner/approvals/pending.html', {
        'settlements': settlements, 'vehicles': vehicles, 'drivers': drivers,
        'vehicle_filter': vehicle_filter, 'driver_filter': driver_filter,
        'date_from': date_from, 'date_to': date_to, 'pending_count': settlements.count(),
    })


@login_required
@staff_member_required
def review_settlement(request, settlement_id):
    settlement = get_object_or_404(DailySettlement.objects.select_related('driver', 'vehicle'), id=settlement_id)
    if settlement.status != 'submitted':
        messages.error(request, 'This settlement is not awaiting approval.')
        return redirect('owner_pending_approvals')
    if request.method == 'POST':
        form = OwnerApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            owner_notes = form.cleaned_data.get('owner_notes', '')
            settlement.owner_notes = owner_notes
            if action == 'approve':
                settlement.status = 'approved'
                settlement.approved_at = timezone.now()
                settlement.approved_by = request.user
                settlement.save()
                messages.success(request, f'Settlement for {settlement.driver.name} approved.')
            else:
                settlement.status = 'rejected'
                settlement.save()
                messages.warning(request, f'Settlement for {settlement.driver.name} rejected.')
            return redirect('owner_pending_approvals')
    else:
        form = OwnerApprovalForm()
    return render(request, 'owner/approvals/review.html', {'settlement': settlement, 'form': form})


@login_required
@staff_member_required
def contract_dashboard(request):
    today = date.today()
    month_start = today.replace(day=1)
    contract_drivers = Driver.objects.filter(vehicle__operating_model='contract', is_active=True)
    contracts = []
    for driver in contract_drivers:
        settlements = DailySettlement.objects.filter(driver=driver, date__gte=month_start, date__lte=today, operating_model='contract', status='approved')
        monthly_gross = sum(s.total_income for s in settlements)
        target = driver.effective_contract_target
        remaining = max(0, target - monthly_gross)
        progress = min(100, (monthly_gross / target * 100)) if target > 0 else 0
        if progress >= 100:
            status = 'Achieved'; status_class = 'success'
        elif progress >= 70:
            status = 'On Track'; status_class = 'warning'
        else:
            status = 'At Risk'; status_class = 'danger'
        if monthly_gross >= target:
            bonus_type = driver.vehicle.contract_success_bonus_type
            if bonus_type == 'fixed':
                estimated_pay = driver.effective_contract_success_bonus_fixed
            elif bonus_type == 'percentage':
                estimated_pay = (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
            else:
                estimated_pay = driver.effective_contract_success_bonus_fixed + (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
        else:
            estimated_pay = (driver.effective_contract_failure_percentage / 100) * monthly_gross
        contracts.append({'driver': driver, 'target': target, 'monthly_gross': monthly_gross, 'remaining': remaining, 'progress': progress, 'status': status, 'status_class': status_class, 'estimated_pay': estimated_pay})
    total_contracts = len(contracts)
    on_target = sum(1 for c in contracts if c['status'] == 'On Track')
    at_risk = sum(1 for c in contracts if c['status'] == 'At Risk')
    achieved = sum(1 for c in contracts if c['status'] == 'Achieved')
    total_potential_bonuses = sum(c['estimated_pay'] for c in contracts if c['status'] == 'Achieved')
    return render(request, 'owner/contract/dashboard.html', {'contracts': contracts, 'total_contracts': total_contracts, 'on_target': on_target, 'at_risk': at_risk, 'achieved': achieved, 'total_potential_bonuses': total_potential_bonuses})


@login_required
@staff_member_required
def contract_detail(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    today = date.today()
    month_start = today.replace(day=1)
    settlements = DailySettlement.objects.filter(driver=driver, date__gte=month_start, date__lte=today, operating_model='contract', status='approved').order_by('date')
    monthly_gross = sum(s.total_income for s in settlements)
    target = driver.effective_contract_target
    remaining = max(0, target - monthly_gross)
    progress = min(100, (monthly_gross / target * 100)) if target > 0 else 0
    _, days_in_month = calendar.monthrange(today.year, today.month)
    days_remaining = days_in_month - today.day
    days_passed = today.day
    daily_average_needed = remaining / days_remaining if days_remaining > 0 else 0
    daily_average_current = monthly_gross / days_passed if days_passed > 0 else 0
    if monthly_gross >= target:
        is_success = True
        bonus_type = driver.vehicle.contract_success_bonus_type
        if bonus_type == 'fixed':
            success_bonus = driver.effective_contract_success_bonus_fixed
        elif bonus_type == 'percentage':
            success_bonus = (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
        else:
            success_bonus = driver.effective_contract_success_bonus_fixed + (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
        driver_pay = success_bonus
        owner_pay = monthly_gross - driver_pay
    else:
        is_success = False
        failure_pct = driver.effective_contract_failure_percentage
        driver_pay = (failure_pct / 100) * monthly_gross
        owner_pay = monthly_gross - driver_pay
        success_bonus = 0
    return render(request, 'owner/contract/detail.html', {
        'driver': driver, 'settlements': settlements, 'monthly_gross': monthly_gross,
        'target': target, 'remaining': remaining, 'progress': progress,
        'days_remaining': days_remaining, 'days_passed': days_passed,
        'daily_average_needed': daily_average_needed, 'daily_average_current': daily_average_current,
        'is_success': is_success, 'success_bonus': success_bonus, 'driver_pay': driver_pay,
        'owner_pay': owner_pay, 'failure_percentage': driver.effective_contract_failure_percentage,
        'bonus_type': driver.vehicle.contract_success_bonus_type,
        'success_bonus_fixed': driver.effective_contract_success_bonus_fixed,
        'success_bonus_percentage': driver.effective_contract_success_bonus_percentage,
    })


@login_required
@staff_member_required
def contract_settle(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    today = date.today()
    month_start = today.replace(day=1)
    if request.method == 'POST':
        settlements = DailySettlement.objects.filter(driver=driver, date__gte=month_start, date__lte=today, operating_model='contract', status='approved')
        monthly_gross = sum(s.total_income for s in settlements)
        total_expenses = sum(s.total_expenses for s in settlements)
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
                driver_pay = driver.effective_contract_success_bonus_fixed + (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
        else:
            driver_pay = (driver.effective_contract_failure_percentage / 100) * monthly_gross
        owner_pay = monthly_gross - driver_pay
        MonthlyContractSummary.objects.update_or_create(driver=driver, year=today.year, month=today.month, defaults={
            'vehicle': driver.vehicle, 'target': target, 'total_gross': monthly_gross,
            'total_expenses': total_expenses, 'gross_profit': gross_profit, 'is_success': is_success,
            'bonus_type': driver.vehicle.contract_success_bonus_type if is_success else '',
            'success_bonus_fixed': driver.effective_contract_success_bonus_fixed if is_success else 0,
            'success_bonus_percentage': driver.effective_contract_success_bonus_percentage if is_success else 0,
            'failure_percentage': driver.effective_contract_failure_percentage if not is_success else 0,
            'driver_pay': driver_pay, 'owner_pay': owner_pay, 'days_worked': settlements.count(),
        })
        return redirect('owner_contract_detail', driver_id=driver.id)
    settlements = DailySettlement.objects.filter(driver=driver, date__gte=month_start, date__lte=today, operating_model='contract', status='approved').order_by('date')
    monthly_gross = sum(s.total_income for s in settlements)
    total_expenses = sum(s.total_expenses for s in settlements)
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
            driver_pay = driver.effective_contract_success_bonus_fixed + (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
    else:
        driver_pay = (driver.effective_contract_failure_percentage / 100) * monthly_gross
    owner_pay = monthly_gross - driver_pay
    return render(request, 'owner/contract/settle.html', {
        'driver': driver, 'settlements': settlements, 'monthly_gross': monthly_gross,
        'total_expenses': total_expenses, 'gross_profit': gross_profit, 'target': target,
        'is_success': is_success, 'driver_pay': driver_pay, 'owner_pay': owner_pay,
        'failure_percentage': driver.effective_contract_failure_percentage,
        'bonus_type': driver.vehicle.contract_success_bonus_type if is_success else 'N/A',
        'success_bonus_fixed': driver.effective_contract_success_bonus_fixed,
        'success_bonus_percentage': driver.effective_contract_success_bonus_percentage,
    })