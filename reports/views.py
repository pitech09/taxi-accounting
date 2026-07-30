from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Avg, Q
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.http import HttpResponse
from django.utils.dateparse import parse_date
import csv
import calendar

from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from contracts.models import MonthlyContractSummary
from cashbook.models import CashTransaction, BankAccount, CashInHand
from cashbook.views import get_total_bank_balance


@login_required
@staff_member_required
def contract_progress(request):
    today = date.today()
    month_start = today.replace(day=1)
    contract_drivers = Driver.objects.filter(vehicle__operating_model='contract', is_active=True)
    contracts = []
    for driver in contract_drivers:
        settlements = DailySettlement.objects.filter(driver=driver, date__gte=month_start, date__lte=today, operating_model='contract')
        monthly_gross = sum(s.total_income for s in settlements)
        target = driver.effective_contract_target
        remaining = max(0, target - monthly_gross)
        progress = min(100, (monthly_gross / target * 100)) if target > 0 else 0
        _, days_in_month = calendar.monthrange(today.year, today.month)
        days_remaining = days_in_month - today.day
        daily_average_needed = remaining / days_remaining if days_remaining > 0 else 0
        if progress >= 100:
            status = 'Achieved'; status_class = 'success'
        elif progress >= 70:
            status = 'On Track'; status_class = 'warning'
        else:
            status = 'At Risk'; status_class = 'danger'
        contracts.append({'driver': driver, 'target': target, 'monthly_gross': monthly_gross, 'remaining': remaining, 'days_remaining': days_remaining, 'daily_average_needed': daily_average_needed, 'progress': progress, 'status': status, 'status_class': status_class})
    return render(request, 'reports/contract_progress.html', {'contracts': contracts, 'month_name': today.strftime('%B %Y')})


@login_required
@staff_member_required
def contract_settlements(request):
    year = request.GET.get('year', date.today().year)
    month = request.GET.get('month', date.today().month)
    summaries = MonthlyContractSummary.objects.filter(year=year, month=month)
    total_contracts = summaries.count()
    successful = summaries.filter(is_success=True).count()
    failed = summaries.filter(is_success=False).count()
    total_bonuses = summaries.filter(is_success=True).aggregate(Sum('driver_pay'))['driver_pay__sum'] or 0
    total_failure_payouts = summaries.filter(is_success=False).aggregate(Sum('driver_pay'))['driver_pay__sum'] or 0
    total_owner_revenue = summaries.aggregate(Sum('owner_pay'))['owner_pay__sum'] or 0
    return render(request, 'reports/contract_settlements.html', {
        'summaries': summaries, 'year': int(year), 'month': int(month),
        'month_name': date(int(year), int(month), 1).strftime('%B %Y'),
        'total_contracts': total_contracts, 'successful': successful, 'failed': failed,
        'total_bonuses': total_bonuses, 'total_failure_payouts': total_failure_payouts,
        'total_owner_revenue': total_owner_revenue, 'years': range(2024, 2031), 'months': range(1, 13),
    })


@login_required
@staff_member_required
def contract_analytics(request):
    driver_success = MonthlyContractSummary.objects.values('driver__name').annotate(total=Count('id'), successes=Count('id', filter=Q(is_success=True)), avg_bonus=Avg('driver_pay', filter=Q(is_success=True)))
    vehicle_success = MonthlyContractSummary.objects.values('vehicle__vehicle_type').annotate(total=Count('id'), successes=Count('id', filter=Q(is_success=True)), avg_bonus=Avg('driver_pay', filter=Q(is_success=True)))
    monthly_trend = MonthlyContractSummary.objects.values('year', 'month').annotate(total=Count('id'), successes=Count('id', filter=Q(is_success=True)), total_bonuses=Sum('driver_pay', filter=Q(is_success=True)), total_owner_revenue=Sum('owner_pay')).order_by('year', 'month')
    return render(request, 'reports/contract_analytics.html', {'driver_success': driver_success, 'vehicle_success': vehicle_success, 'monthly_trend': monthly_trend})


# ── Cash Book Reports ────────────────────────────────────────────

@login_required
@staff_member_required
def cashbook_report(request):
    today = date.today()
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    days = request.GET.get('days')  # optional: e.g., ?days=30

    # Default to current month if no dates provided
    if date_from_str:
        start_date = parse_date(date_from_str)
    else:
        start_date = today.replace(day=1)  # first day of current month

    if date_to_str:
        end_date = parse_date(date_to_str)
    else:
        end_date = today

    # If a 'days' parameter is given, override start_date
    if days:
        try:
            days_int = int(days)
            start_date = today - timedelta(days=days_int)
            end_date = today
        except (ValueError, TypeError):
            pass

    # Filter transactions
    date_from = start_date
    date_to = end_date
    transactions = CashTransaction.objects.filter(date__gte=start_date, date__lte=end_date).select_related('bank_account', 'settlement', 'settlement__driver').order_by('date', 'id')

    cash_in_types = ['addition', 'transfer_from_bank', 'settlement_collection']
    cash_out_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash', 'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']
    prior_date = start_date - timedelta(days=1)
    prior_in = CashTransaction.objects.filter(date__lte=prior_date, transaction_type__in=cash_in_types).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    prior_out = CashTransaction.objects.filter(date__lte=prior_date, transaction_type__in=cash_out_types).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    opening_balance = prior_in - prior_out

    running_balance = opening_balance
    entries = []
    total_in = Decimal('0')
    total_out = Decimal('0')
    for t in transactions:
        if t.is_inflow:
            running_balance += t.amount; total_in += t.amount
        else:
            running_balance -= t.amount; total_out += t.amount
        entries.append({'date': t.date, 'description': t.notes or t.get_transaction_type_display(), 'type': t.get_transaction_type_display(), 'category': t.get_category_display(), 'in': t.amount if t.is_inflow else None, 'out': t.amount if t.is_outflow else None, 'balance': running_balance, 'transaction': t})
    closing_balance = running_balance
    return render(request, 'reports/cashbook.html', {'entries': entries, 'date_from': date_from, 'date_to': date_to, 'opening_balance': opening_balance, 'closing_balance': closing_balance, 'total_in': total_in, 'total_out': total_out, 'net_flow': total_in - total_out})


@login_required
@staff_member_required
def cashbook_report_csv(request):
    today = date.today()
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')

    if date_from_str:
        date_from = parse_date(date_from_str)
    else:
        date_from = today.replace(day=1)

    if date_to_str:
        date_to = parse_date(date_to_str)
    else:
        date_to = today

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="cashbook_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Type', 'Category', 'In (M)', 'Out (M)', 'Balance (M)'])
    transactions = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to).order_by('date', 'id')

    cash_in_types = ['addition', 'transfer_from_bank', 'settlement_collection']
    cash_out_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash', 'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']
    prior_date = date_from - timedelta(days=1)
    prior_in = CashTransaction.objects.filter(date__lte=prior_date, transaction_type__in=cash_in_types).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    prior_out = CashTransaction.objects.filter(date__lte=prior_date, transaction_type__in=cash_out_types).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    opening_balance = prior_in - prior_out
    running_balance = opening_balance
    writer.writerow([date_from.strftime('%Y-%m-%d'), 'Opening Balance', '', '', '', '', f'{running_balance}'])
    for t in transactions:
        if t.is_inflow:
            running_balance += t.amount
            writer.writerow([t.date.strftime('%Y-%m-%d'), t.notes or t.get_transaction_type_display(), t.get_transaction_type_display(), t.get_category_display(), t.amount, '', f'{running_balance}'])
        else:
            running_balance -= t.amount
            writer.writerow([t.date.strftime('%Y-%m-%d'), t.notes or t.get_transaction_type_display(), t.get_transaction_type_display(), t.get_category_display(), '', t.amount, f'{running_balance}'])
    writer.writerow([])
    writer.writerow(['', 'TOTALS', '', '', '', '', ''])
    total_in = sum(t.amount for t in transactions if t.is_inflow)
    total_out = sum(t.amount for t in transactions if t.is_outflow)
    writer.writerow(['', 'Total In', '', '', total_in, '', ''])
    writer.writerow(['', 'Total Out', '', '', '', total_out, ''])
    writer.writerow(['', 'Closing Balance', '', '', '', '', f'{running_balance}'])
    return response


@login_required
@staff_member_required
def bank_reconciliation(request):
    today = date.today()
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')

    if date_from_str:
        date_from = parse_date(date_from_str)
    else:
        date_from = today.replace(day=1)

    if date_to_str:
        date_to = parse_date(date_to_str)
    else:
        date_to = today

    bank_id = request.GET.get('bank', '')
    bank_accounts = BankAccount.objects.filter(is_active=True)
    transactions = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, transaction_type__in=['transfer_to_bank', 'transfer_from_bank']).select_related('bank_account')
    if bank_id:
        transactions = transactions.filter(bank_account_id=bank_id)
        selected_bank = BankAccount.objects.get(id=bank_id)
    else:
        selected_bank = None
    deposits = transactions.filter(transaction_type='transfer_to_bank').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    withdrawals = transactions.filter(transaction_type='transfer_from_bank').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    if selected_bank:
        prior_deposits = CashTransaction.objects.filter(date__lt=date_from, transaction_type='transfer_to_bank', bank_account=selected_bank).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        prior_withdrawals = CashTransaction.objects.filter(date__lt=date_from, transaction_type='transfer_from_bank', bank_account=selected_bank).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        opening_balance = selected_bank.opening_balance + prior_deposits - prior_withdrawals
        system_closing = opening_balance + deposits - withdrawals
    else:
        opening_balance = sum(b.opening_balance for b in bank_accounts)
        system_closing = opening_balance + deposits - withdrawals
    actual_closing = request.GET.get('actual_closing', '')
    difference = None
    if actual_closing:
        try:
            actual_closing = Decimal(str(actual_closing))
            difference = system_closing - actual_closing
        except Exception:
            actual_closing = ''
    return render(request, 'reports/bank_reconciliation.html', {
        'bank_accounts': bank_accounts, 'selected_bank': selected_bank, 'bank_id': bank_id,
        'transactions': transactions.order_by('date'), 'date_from': date_from, 'date_to': date_to,
        'opening_balance': opening_balance, 'deposits': deposits, 'withdrawals': withdrawals,
        'system_closing': system_closing, 'actual_closing': actual_closing, 'difference': difference,
    })


@login_required
@staff_member_required
def expense_report(request):
    today = date.today()
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')

    if date_from_str:
        date_from = parse_date(date_from_str)
    else:
        date_from = today.replace(day=1)

    if date_to_str:
        date_to = parse_date(date_to_str)
    else:
        date_to = today

    category_filter = request.GET.get('category', '')
    expenses = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, transaction_type__in=['expense_cash', 'expense_bank', 'petty_cash']).select_related('bank_account', 'settlement__driver')
    if category_filter:
        expenses = expenses.filter(category=category_filter)
    category_totals = expenses.values('category').annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    income = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, transaction_type__in=['addition', 'transfer_from_bank']).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    chart_labels = [dict(CashTransaction.CATEGORY_CHOICES).get(c['category'], c['category']) for c in category_totals]
    chart_data = [float(c['total']) for c in category_totals]
    return render(request, 'reports/expenses.html', {
        'expenses': expenses.order_by('-date'), 'category_totals': category_totals,
        'total_expenses': total_expenses, 'income': income, 'net': income - total_expenses,
        'date_from': date_from, 'date_to': date_to, 'category_filter': category_filter,
        'category_choices': CashTransaction.CATEGORY_CHOICES, 'chart_labels': chart_labels, 'chart_data': chart_data,
    })


@login_required
@staff_member_required
def cash_flow_report(request):
    today = date.today()
    period = request.GET.get('period', 'month')
    if period == 'quarter':
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        date_from = date(today.year, quarter_start_month, 1)
        date_to = today
        period_label = f"Q{(today.month - 1) // 3 + 1} {today.year}"
    elif period == 'year':
        date_from = date(today.year, 1, 1)
        date_to = today
        period_label = str(today.year)
    else:
        date_from = today.replace(day=1)
        date_to = today
        period_label = today.strftime('%B %Y')

    cash_in_types = ['addition', 'transfer_from_bank', 'settlement_collection']
    cash_out_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash', 'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']

    settlement_collections = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, category='settlement_collection').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    other_income = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, category__in=['other_income', 'loan_income']).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    bank_withdrawals = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, transaction_type='transfer_from_bank').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    total_inflows = settlement_collections + other_income + bank_withdrawals

    expenses = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, transaction_type__in=['expense_cash', 'expense_bank', 'petty_cash']).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    bank_deposits = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, transaction_type='transfer_to_bank').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    withdrawals = CashTransaction.objects.filter(date__gte=date_from, date__lte=date_to, transaction_type='withdrawal').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    total_outflows = expenses + bank_deposits + withdrawals
    net_cash_flow = total_inflows - total_outflows

    prior_date = date_from - timedelta(days=1)
    prior_in = CashTransaction.objects.filter(date__lte=prior_date, transaction_type__in=cash_in_types).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    prior_out = CashTransaction.objects.filter(date__lte=prior_date, transaction_type__in=cash_out_types).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    opening_balance = prior_in - prior_out
    closing_balance = opening_balance + net_cash_flow

    chart_labels = []
    chart_data = []
    current = date_from
    while current <= date_to:
        day_in = CashTransaction.objects.filter(date=current, transaction_type__in=cash_in_types).aggregate(Sum('amount'))['amount__sum'] or 0
        day_out = CashTransaction.objects.filter(date=current, transaction_type__in=cash_out_types).aggregate(Sum('amount'))['amount__sum'] or 0
        chart_labels.append(current.strftime('%d %b'))
        chart_data.append(float(day_in - day_out))
        current += timedelta(days=1)

    return render(request, 'reports/cash_flow.html', {
        'period': period, 'period_label': period_label, 'date_from': date_from, 'date_to': date_to,
        'settlement_collections': settlement_collections, 'other_income': other_income,
        'bank_withdrawals': bank_withdrawals, 'total_inflows': total_inflows,
        'expenses': expenses, 'bank_deposits': bank_deposits, 'withdrawals': withdrawals,
        'total_outflows': total_outflows, 'net_cash_flow': net_cash_flow,
        'opening_balance': opening_balance, 'closing_balance': closing_balance,
        'chart_labels': chart_labels, 'chart_data': chart_data,
    })