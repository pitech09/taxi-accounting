from decimal import Decimal
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Q
from django.http import HttpResponse
import csv

from .models import CashInHand, BankAccount, CashTransaction, DailyCashBook
from .forms import (
    CashTransactionForm, BankAccountForm,
    BankDepositForm, BankWithdrawalForm, ExpenseForm,
)
from accounts.models import SystemSettings


def get_total_bank_balance():
    """Calculate total balance across all active bank accounts."""
    return BankAccount.objects.filter(is_active=True).aggregate(
        Sum('current_balance')
    )['current_balance__sum'] or Decimal('0')


def get_settings():
    """Get or create system settings."""
    settings, _ = SystemSettings.objects.get_or_create(pk=1)
    return settings


@login_required
@staff_member_required
def cashbook_dashboard(request):
    """Cash book dashboard with summary cards and recent transactions."""
    today = date.today()
    month_start = today.replace(day=1)
    settings = get_settings()

    cash_in_hand = CashInHand.get_balance()
    total_bank = get_total_bank_balance()

    cash_in_types = ['addition', 'transfer_from_bank', 'settlement_collection']
    cash_out_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash',
                      'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']

    mtd_cash_in = CashTransaction.objects.filter(
        date__gte=month_start, date__lte=today,
        transaction_type__in=cash_in_types,
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    mtd_cash_out = CashTransaction.objects.filter(
        date__gte=month_start, date__lte=today,
        transaction_type__in=cash_out_types,
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    net_cash_flow = mtd_cash_in - mtd_cash_out

    recent_transactions = CashTransaction.objects.select_related(
        'bank_account', 'settlement', 'settlement__driver'
    ).order_by('-date', '-created_at')[:20]

    bank_accounts = BankAccount.objects.filter(is_active=True)

    # Alerts
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

    # Cash flow chart data (last 7 days)
    chart_labels = []
    chart_in = []
    chart_out = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime('%d %b'))
        day_in = CashTransaction.objects.filter(
            date=d,
            transaction_type__in=cash_in_types,
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        day_out = CashTransaction.objects.filter(
            date=d,
            transaction_type__in=cash_out_types,
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        chart_in.append(float(day_in))
        chart_out.append(float(day_out))

    context = {
        'cash_in_hand': cash_in_hand,
        'total_bank': total_bank,
        'mtd_cash_in': mtd_cash_in,
        'mtd_cash_out': mtd_cash_out,
        'net_cash_flow': net_cash_flow,
        'recent_transactions': recent_transactions,
        'bank_accounts': bank_accounts,
        'alerts': alerts,
        'chart_labels': chart_labels,
        'chart_in': chart_in,
        'chart_out': chart_out,
    }
    return render(request, 'owner/cashbook/dashboard.html', context)


@login_required
@staff_member_required
def cashbook_entries(request):
    """List all cash transactions with filters."""
    transactions = CashTransaction.objects.select_related(
        'bank_account', 'settlement', 'settlement__driver'
    ).order_by('-date', '-created_at')

    # Filters
    type_filter = request.GET.get('type', '')
    category_filter = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)
    if category_filter:
        transactions = transactions.filter(category=category_filter)
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)

    context = {
        'transactions': transactions,
        'type_filter': type_filter,
        'category_filter': category_filter,
        'date_from': date_from,
        'date_to': date_to,
        'transaction_types': CashTransaction.TRANSACTION_TYPES,
        'category_choices': CashTransaction.CATEGORY_CHOICES,
    }
    return render(request, 'owner/cashbook/entries.html', context)


@login_required
@staff_member_required
def cashbook_add(request):
    """Record a new cash transaction."""
    cash_in_hand = CashInHand.get_balance()

    if request.method == 'POST':
        form = CashTransactionForm(request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.save()
            messages.success(
                request,
                f'Transaction recorded: {transaction.get_transaction_type_display()} - M {transaction.amount:.2f}'
            )
            return redirect('owner_cashbook_entries')
    else:
        form = CashTransactionForm()

    context = {
        'form': form,
        'cash_in_hand': cash_in_hand,
        'title': 'Record Cash Transaction',
    }
    return render(request, 'owner/cashbook/form.html', context)


@login_required
@staff_member_required
def cashbook_edit(request, transaction_id):
    """Edit a cash transaction."""
    transaction = get_object_or_404(CashTransaction, id=transaction_id)
    cash_in_hand = CashInHand.get_balance()

    if request.method == 'POST':
        form = CashTransactionForm(request.POST, request.FILES, instance=transaction)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.save()
            messages.success(request, 'Transaction updated successfully.')
            return redirect('owner_cashbook_entries')
    else:
        form = CashTransactionForm(instance=transaction)

    context = {
        'form': form,
        'transaction': transaction,
        'cash_in_hand': cash_in_hand,
        'title': 'Edit Cash Transaction',
    }
    return render(request, 'owner/cashbook/form.html', context)


@login_required
@staff_member_required
def cashbook_delete(request, transaction_id):
    """Delete a cash transaction."""
    transaction = get_object_or_404(CashTransaction, id=transaction_id)
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully.')
        return redirect('owner_cashbook_entries')
    return render(request, 'owner/cashbook/delete.html', {'transaction': transaction})


@login_required
@staff_member_required
def cashbook_export_csv(request):
    """Export cash transactions to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="cash_transactions.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Type', 'Category', 'Amount', 'Cash Balance After',
        'Bank Account', 'Bank Balance After', 'Reference', 'Notes',
        'Settlement', 'Created By',
    ])

    transactions = CashTransaction.objects.select_related(
        'bank_account', 'settlement', 'settlement__driver', 'created_by'
    ).order_by('-date', '-created_at')

    for t in transactions:
        writer.writerow([
            t.date, t.get_transaction_type_display(), t.get_category_display(),
            t.amount, t.cash_balance_after,
            t.bank_account.name if t.bank_account else '', t.bank_balance_after,
            t.reference, t.notes,
            f"{t.settlement.driver.name} - {t.settlement.date}" if t.settlement else '',
            t.created_by.username if t.created_by else '',
        ])

    return response


@login_required
@staff_member_required
def cashbook_ledger(request):
    """Full ledger with running balance."""
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    type_filter = request.GET.get('type', '')
    category_filter = request.GET.get('category', '')

    transactions = CashTransaction.objects.select_related(
        'bank_account', 'settlement', 'settlement__driver'
    ).order_by('date', 'created_at')

    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)
    if category_filter:
        transactions = transactions.filter(category=category_filter)
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)

    # Opening balance (before date_from)
    cash_in_types = ['addition', 'transfer_from_bank', 'settlement_collection']
    cash_out_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash',
                      'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']

    if date_from:
        opening_in = CashTransaction.objects.filter(
            date__lt=date_from,
            transaction_type__in=cash_in_types,
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        opening_out = CashTransaction.objects.filter(
            date__lt=date_from,
            transaction_type__in=cash_out_types,
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        opening_balance = opening_in - opening_out
    else:
        opening_balance = CashInHand.get_balance() - (
            CashTransaction.objects.filter(transaction_type__in=cash_in_types)
            .aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        ) + (
            CashTransaction.objects.filter(transaction_type__in=cash_out_types)
            .aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        )

    total_debits = sum(t.amount for t in transactions if t.is_inflow)
    total_credits = sum(t.amount for t in transactions if t.is_outflow)
    closing_balance = opening_balance + total_debits - total_credits

    context = {
        'transactions': transactions,
        'opening_balance': opening_balance,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'closing_balance': closing_balance,
        'date_from': date_from,
        'date_to': date_to,
        'type_filter': type_filter,
        'category_filter': category_filter,
        'transaction_types': CashTransaction.TRANSACTION_TYPES,
        'category_choices': CashTransaction.CATEGORY_CHOICES,
    }
    return render(request, 'owner/cashbook/ledger.html', context)


# ── Bank Account Management ──────────────────────────────────────

@login_required
@staff_member_required
def bank_list(request):
    """List all bank accounts."""
    accounts = BankAccount.objects.all().order_by('name')
    total_active = BankAccount.objects.filter(is_active=True).aggregate(
        Sum('current_balance')
    )['current_balance__sum'] or Decimal('0')
    context = {'accounts': accounts, 'total_active': total_active}
    return render(request, 'owner/cashbook/banks.html', context)


@login_required
@staff_member_required
def bank_add(request):
    """Add a new bank account."""
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank account added successfully.')
            return redirect('owner_cashbook_banks')
    else:
        form = BankAccountForm()
    context = {'form': form, 'title': 'Add Bank Account'}
    return render(request, 'owner/cashbook/bank_form.html', context)


@login_required
@staff_member_required
def bank_edit(request, bank_id):
    """Edit a bank account."""
    account = get_object_or_404(BankAccount, id=bank_id)
    if request.method == 'POST':
        form = BankAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank account updated successfully.')
            return redirect('owner_cashbook_banks')
    else:
        form = BankAccountForm(instance=account)
    context = {'form': form, 'account': account, 'title': 'Edit Bank Account'}
    return render(request, 'owner/cashbook/bank_form.html', context)


@login_required
@staff_member_required
def bank_delete(request, bank_id):
    """Delete a bank account."""
    account = get_object_or_404(BankAccount, id=bank_id)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Bank account deleted successfully.')
        return redirect('owner_cashbook_banks')
    return render(request, 'owner/cashbook/bank_delete.html', {'account': account})


@login_required
@staff_member_required
def bank_deposit(request):
    """Record a bank deposit (transfer from cash to bank)."""
    cash_in_hand = CashInHand.get_balance()

    if request.method == 'POST':
        form = BankDepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            bank_account = form.cleaned_data['bank_account']
            txn_date = form.cleaned_data['date']
            reference = form.cleaned_data.get('reference', '')
            notes = form.cleaned_data.get('notes', '')

            CashTransaction.objects.create(
                transaction_type='transfer_to_bank',
                category='other_income',
                amount=amount,
                date=txn_date,
                bank_account=bank_account,
                reference=reference,
                notes=notes or f'Bank deposit to {bank_account.name}',
                created_by=request.user,
            )
            messages.success(request, f'Bank deposit of M {amount:.2f} recorded to {bank_account.name}.')
            return redirect('owner_cashbook_dashboard')
    else:
        form = BankDepositForm()

    context = {
        'form': form,
        'cash_in_hand': cash_in_hand,
        'title': 'Record Bank Deposit',
    }
    return render(request, 'owner/cashbook/deposit.html', context)


@login_required
@staff_member_required
def bank_withdraw(request):
    """Record a bank withdrawal (transfer from bank to cash)."""
    cash_in_hand = CashInHand.get_balance()

    if request.method == 'POST':
        form = BankWithdrawalForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            bank_account = form.cleaned_data['bank_account']
            txn_date = form.cleaned_data['date']
            reference = form.cleaned_data.get('reference', '')
            notes = form.cleaned_data.get('notes', '')

            CashTransaction.objects.create(
                transaction_type='transfer_from_bank',
                category='other_income',
                amount=amount,
                date=txn_date,
                bank_account=bank_account,
                reference=reference,
                notes=notes or f'Bank withdrawal from {bank_account.name}',
                created_by=request.user,
            )
            messages.success(request, f'Bank withdrawal of M {amount:.2f} recorded from {bank_account.name}.')
            return redirect('owner_cashbook_dashboard')
    else:
        form = BankWithdrawalForm()

    context = {
        'form': form,
        'cash_in_hand': cash_in_hand,
        'title': 'Record Bank Withdrawal',
    }
    return render(request, 'owner/cashbook/withdraw.html', context)


# ── Expense ──────────────────────────────────────────────────────

@login_required
@staff_member_required
def record_expense(request):
    """Record a business expense."""
    cash_in_hand = CashInHand.get_balance()

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.cleaned_data['category']
            amount = form.cleaned_data['amount']
            txn_date = form.cleaned_data['date']
            payment_method = form.cleaned_data['payment_method']
            bank_account = form.cleaned_data.get('bank_account')
            reference = form.cleaned_data.get('reference', '')
            receipt_photo = form.cleaned_data.get('receipt_photo')
            notes = form.cleaned_data.get('notes', '')

            txn_type = 'expense_bank' if payment_method == 'bank' else 'expense_cash'

            CashTransaction.objects.create(
                transaction_type=txn_type,
                category=category,
                amount=amount,
                date=txn_date,
                bank_account=bank_account if payment_method == 'bank' else None,
                reference=reference,
                receipt_photo=receipt_photo,
                notes=notes,
                created_by=request.user,
            )
            messages.success(request, f'Expense recorded: {form.cleaned_data["category"]} - M {amount:.2f}')
            return redirect('owner_cashbook_dashboard')
    else:
        form = ExpenseForm()

    context = {
        'form': form,
        'cash_in_hand': cash_in_hand,
        'title': 'Record Business Expense',
    }
    return render(request, 'owner/cashbook/expense.html', context)


@login_required
@staff_member_required
def record_petty_cash(request):
    """Record a petty cash transaction."""
    cash_in_hand = CashInHand.get_balance()

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.cleaned_data['category']
            amount = form.cleaned_data['amount']
            txn_date = form.cleaned_data['date']
            reference = form.cleaned_data.get('reference', '')
            receipt_photo = form.cleaned_data.get('receipt_photo')
            notes = form.cleaned_data.get('notes', '')

            CashTransaction.objects.create(
                transaction_type='petty_cash',
                category='petty_cash_expense',
                amount=amount,
                date=txn_date,
                reference=reference,
                receipt_photo=receipt_photo,
                notes=notes,
                created_by=request.user,
            )
            messages.success(request, f'Petty cash recorded: M {amount:.2f}')
            return redirect('owner_cashbook_dashboard')
    else:
        form = ExpenseForm()

    context = {
        'form': form,
        'cash_in_hand': cash_in_hand,
        'title': 'Record Petty Cash',
    }
    return render(request, 'owner/cashbook/expense.html', context)