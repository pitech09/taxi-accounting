"""
Report views for the Taxi Accounting System.
All views require staff authentication.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.utils import timezone
from datetime import date, datetime, timedelta
import calendar
import csv
from io import StringIO

from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from cashbook.models import CashInHand, BankAccount, CashTransaction
from accounts.models import SystemSettings
from contracts.models import MonthlyContractSummary


def _owner_required(view_func):
    from django.contrib.auth.decorators import user_passes_test
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_date_range(request):
    """Extract start/end dates from GET params, defaulting to current month."""
    today = date.today()
    start_date = request.GET.get('start_date') or today.replace(day=1)
    end_date = request.GET.get('end_date') or today
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    return start_date, end_date


# ------------------------------------------------------------------
# Report index
# ------------------------------------------------------------------
@_owner_required
def report_index(request):
    return render(request, 'reports/index.html')


# ------------------------------------------------------------------
# Daily fleet summary
# ------------------------------------------------------------------
@_owner_required
def daily_fleet_summary(request):
    """Daily fleet summary report."""
    target_date = request.GET.get('date') or date.today()
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

    settlements = DailySettlement.objects.filter(
        date=target_date, status='approved'
    ).select_related('driver', 'vehicle')

    summary = settlements.aggregate(
        total_income=Sum('total_income'),
        total_expenses=Sum('total_expenses'),
        total_gross=Sum('gross_profit'),
        total_driver_pay=Sum('driver_pay'),
        total_owner=Sum('total_owner_collected'),
    )

    context = {
        'target_date': target_date,
        'settlements': settlements,
        'summary': summary,
    }
    return render(request, 'reports/daily_fleet_summary.html', context)


# ------------------------------------------------------------------
# Monthly P&L per vehicle
# ------------------------------------------------------------------
@_owner_required
def monthly_pnl(request):
    """Monthly profit & loss per vehicle."""
    start_date, end_date = _get_date_range(request)
    vehicle_id = request.GET.get('vehicle')

    settlements = DailySettlement.objects.filter(
        status='approved', date__gte=start_date, date__lte=end_date
    )
    if vehicle_id:
        settlements = settlements.filter(vehicle_id=vehicle_id)

    # Aggregate by vehicle
    vehicle_summaries = []
    vehicles = Vehicle.objects.filter(is_active=True)
    for v in vehicles:
        v_settlements = settlements.filter(vehicle=v)
        if not v_settlements.exists():
            continue
        agg = v_settlements.aggregate(
            total_income=Sum('total_income'),
            total_expenses=Sum('total_expenses'),
            gross_profit=Sum('gross_profit'),
            driver_pay=Sum('driver_pay'),
            owner_collection=Sum('total_owner_collected'),
        )
        vehicle_summaries.append({
            'vehicle': v,
            'total_income': agg['total_income'] or 0,
            'total_expenses': agg['total_expenses'] or 0,
            'gross_profit': agg['gross_profit'] or 0,
            'driver_pay': agg['driver_pay'] or 0,
            'owner_collection': agg['owner_collection'] or 0,
        })

    totals = settlements.aggregate(
        total_income=Sum('total_income'),
        total_expenses=Sum('total_expenses'),
        gross_profit=Sum('gross_profit'),
        driver_pay=Sum('driver_pay'),
        owner_collection=Sum('total_owner_collected'),
    )

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'vehicle_summaries': vehicle_summaries,
        'totals': totals,
        'vehicles': vehicles,
    }
    return render(request, 'reports/monthly_pnl.html', context)


# ------------------------------------------------------------------
# Cash book ledger report
# ------------------------------------------------------------------
@_owner_required
def cashbook_report(request):
    """Cash book ledger report."""
    start_date, end_date = _get_date_range(request)

    transactions = CashTransaction.objects.filter(
        date__gte=start_date, date__lte=end_date
    ).order_by('date', 'created_at')

    additions = transactions.filter(
        transaction_type__in=['addition', 'transfer_from_bank', 'settlement_collection']
    ).aggregate(total=Sum('amount'))['total'] or 0
    withdrawals = transactions.filter(
        transaction_type__in=['withdrawal', 'transfer_to_bank', 'expense_cash',
                              'petty_cash', 'salary_payment', 'commission_payment',
                              'bonus_payment', 'loan_repayment']
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'transactions': transactions,
        'additions': additions,
        'withdrawals': withdrawals,
        'net': additions - withdrawals,
        'cash_balance': CashInHand.get_balance(),
    }
    return render(request, 'reports/cashbook.html', context)


@_owner_required
def cashbook_report_csv(request):
    """Export cash book report to CSV."""
    start_date, end_date = _get_date_range(request)

    transactions = CashTransaction.objects.filter(
        date__gte=start_date, date__lte=end_date
    ).order_by('date', 'created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cashbook_{start_date}_{end_date}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Bank', 'Cash After', 'Bank After', 'Reference', 'Notes'])
    for t in transactions:
        writer.writerow([
            t.date, t.get_transaction_type_display(), t.get_category_display(),
            t.amount, t.bank_account.name if t.bank_account else '-',
            t.cash_balance_after or '-', t.bank_balance_after or '-',
            t.reference or '-', t.notes or '-',
        ])
    return response


# ------------------------------------------------------------------
# Bank reconciliation
# ------------------------------------------------------------------
@_owner_required
def bank_reconciliation(request):
    """Bank reconciliation report."""
    start_date, end_date = _get_date_range(request)
    bank_id = request.GET.get('bank')

    banks = BankAccount.objects.filter(is_active=True)
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'banks': banks,
    }

    if bank_id:
        bank = get_object_or_404_bank(bank_id)
        transactions = CashTransaction.objects.filter(
            bank_account=bank, date__gte=start_date, date__lte=end_date
        ).order_by('date', 'created_at')

        deposits = transactions.filter(
            transaction_type__in=['transfer_to_bank', 'transfer_from_bank']
        ).aggregate(total=Sum('amount'))['total'] or 0

        context.update({
            'bank': bank,
            'transactions': transactions,
            'deposits': deposits,
            'current_balance': bank.current_balance,
        })

    return render(request, 'reports/bank_reconciliation.html', context)


def get_object_or_404_bank(bank_id):
    from django.shortcuts import get_object_or_404
    return get_object_or_404(BankAccount, id=bank_id)


# ------------------------------------------------------------------
# Expense report
# ------------------------------------------------------------------
@_owner_required
def expense_report(request):
    """Expense report."""
    start_date, end_date = _get_date_range(request)
    category = request.GET.get('category')

    expenses = CashTransaction.objects.filter(
        transaction_type__in=['expense_cash', 'expense_bank', 'petty_cash',
                              'salary_payment', 'commission_payment', 'bonus_payment',
                              'loan_repayment'],
        date__gte=start_date, date__lte=end_date,
    )
    if category:
        expenses = expenses.filter(category=category)

    expenses = expenses.order_by('-date', '-created_at')

    by_category = expenses.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')

    total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'expenses': expenses,
        'by_category': by_category,
        'total': total,
    }
    return render(request, 'reports/expenses.html', context)


# ------------------------------------------------------------------
# Cash flow statement
# ------------------------------------------------------------------
@_owner_required
def cash_flow_report(request):
    """Cash flow statement."""
    start_date, end_date = _get_date_range(request)

    transactions = CashTransaction.objects.filter(
        date__gte=start_date, date__lte=end_date
    )

    cash_in = transactions.filter(
        transaction_type__in=['addition', 'transfer_from_bank', 'settlement_collection']
    ).aggregate(total=Sum('amount'))['total'] or 0

    cash_out = transactions.filter(
        transaction_type__in=['withdrawal', 'transfer_to_bank', 'expense_cash',
                              'petty_cash', 'salary_payment', 'commission_payment',
                              'bonus_payment', 'loan_repayment']
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'cash_in': cash_in,
        'cash_out': cash_out,
        'net_flow': cash_in - cash_out,
        'opening_balance': CashInHand.get_balance() - (cash_in - cash_out),
        'closing_balance': CashInHand.get_balance(),
    }
    return render(request, 'reports/cash_flow.html', context)


# ------------------------------------------------------------------
# Contract progress report
# ------------------------------------------------------------------
@_owner_required
def contract_progress(request):
    """Contract progress report."""
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    month_start = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)
    month_end = date(year, month, days_in_month)

    contract_drivers = Driver.objects.filter(
        vehicle__operating_model='contract', is_active=True
    ).select_related('vehicle')

    contracts = []
    for driver in contract_drivers:
        settlements = DailySettlement.objects.filter(
            driver=driver, status='approved',
            date__gte=month_start, date__lte=month_end
        )
        monthly_gross = settlements.aggregate(total=Sum('total_income'))['total'] or 0
        target = driver.effective_contract_target
        progress = (monthly_gross / target * 100) if target > 0 else 0
        days_remaining = max(0, days_in_month - today.day) if month == today.month and year == today.year else days_in_month
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

    month_name = calendar.month_name[month]
    context = {
        'contracts': contracts,
        'month': month,
        'year': year,
        'month_name': month_name,
    }
    return render(request, 'reports/contract_progress.html', context)


# ------------------------------------------------------------------
# Contract settlements report
# ------------------------------------------------------------------
@_owner_required
def contract_settlements(request):
    """Historical contract settlements report."""
    summaries = MonthlyContractSummary.objects.all().order_by('-year', '-month')

    start_date, end_date = _get_date_range(request)
    summaries = summaries.filter(
        models_Q_date_range(year=start_date.year, month=start_date.month)
    ) if False else summaries  # placeholder – full date filtering below

    # Simple year/month filter
    year = request.GET.get('year')
    month = request.GET.get('month')
    if year:
        summaries = summaries.filter(year=int(year))
    if month:
        summaries = summaries.filter(month=int(month))

    total_driver_pay = summaries.aggregate(total=Sum('driver_pay'))['total'] or 0
    total_owner_pay = summaries.aggregate(total=Sum('owner_pay'))['total'] or 0
    total_gross = summaries.aggregate(total=Sum('total_gross'))['total'] or 0

    context = {
        'summaries': summaries,
        'total_driver_pay': total_driver_pay,
        'total_owner_pay': total_owner_pay,
        'total_gross': total_gross,
    }
    return render(request, 'reports/contract_settlements.html', context)


def models_Q_date_range(year, month):
    """Helper – not used, kept for clarity."""
    from django.db.models import Q
    return Q()


# ------------------------------------------------------------------
# Contract analytics
# ------------------------------------------------------------------
@_owner_required
def contract_analytics(request):
    """Contract analytics with charts."""
    summaries = MonthlyContractSummary.objects.all().order_by('-year', '-month')

    total_success = summaries.filter(is_success=True).count()
    total_failure = summaries.filter(is_success=False).count()
    total_driver_pay = summaries.aggregate(total=Sum('driver_pay'))['total'] or 0
    total_owner_pay = summaries.aggregate(total=Sum('owner_pay'))['total'] or 0

    # Data for chart
    chart_labels = [f"{s.month}/{s.year}" for s in summaries[:12]]
    chart_driver = [float(s.driver_pay) for s in summaries[:12]]
    chart_owner = [float(s.owner_pay) for s in summaries[:12]]

    context = {
        'summaries': summaries,
        'total_success': total_success,
        'total_failure': total_failure,
        'total_driver_pay': total_driver_pay,
        'total_owner_pay': total_owner_pay,
        'chart_labels': chart_labels,
        'chart_driver': chart_driver,
        'chart_owner': chart_owner,
    }
    return render(request, 'reports/contract_analytics.html', context)


# ------------------------------------------------------------------
# Tax report
# ------------------------------------------------------------------
@_owner_required
def tax_report(request):
    """Tax report – summarises taxable income and expenses."""
    start_date, end_date = _get_date_range(request)

    settlements = DailySettlement.objects.filter(
        status='approved', date__gte=start_date, date__lte=end_date
    )

    total_income = settlements.aggregate(total=Sum('total_income'))['total'] or 0
    total_expenses = settlements.aggregate(total=Sum('total_expenses'))['total'] or 0
    gross_profit = total_income - total_expenses

    # Fixed costs
    fixed_costs = Vehicle.objects.filter(is_active=True).aggregate(
        total_insurance=Sum('insurance'),
        total_permit=Sum('permit_cost'),
        total_loan=Sum('loan_payment'),
    )
    monthly_fixed = sum(
        (v.insurance + (v.permit_cost / 12) + v.loan_payment)
        for v in Vehicle.objects.filter(is_active=True)
    )

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'gross_profit': gross_profit,
        'monthly_fixed_costs': monthly_fixed,
        'taxable_income': gross_profit - monthly_fixed,
    }
    return render(request, 'reports/tax.html', context)
