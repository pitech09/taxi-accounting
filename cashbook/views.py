"""
Cashbook views for the Owner portal.
All views require staff authentication.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import date
from django.core.exceptions import ValidationError  # <-- ADDED

from .models import CashInHand, BankAccount, CashTransaction
from .forms import BankAccountForm, CashTransactionForm, ExpenseForm, DepositForm
from accounts.models import SystemSettings


def _owner_required(view_func):
    """Decorator: require staff user."""
    from django.contrib.auth.decorators import user_passes_test
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ------------------------------------------------------------------
# Cashbook dashboard
# ------------------------------------------------------------------
@_owner_required
def cashbook_dashboard(request):
    """Cash book dashboard with balances and recent transactions."""
    settings = SystemSettings.get_settings()
    cash_balance = CashInHand.get_balance()
    bank_accounts = BankAccount.objects.filter(is_active=True)
    bank_total = bank_accounts.aggregate(total=Sum('current_balance'))['total'] or 0

    recent_transactions = CashTransaction.objects.all().order_by('-created_at')[:10]

    # Check for low balance alerts
    alerts = []
    if cash_balance < settings.cash_alert_threshold:
        alerts.append(f'Cash in Hand is below threshold (M {settings.cash_alert_threshold})')
    for account in bank_accounts:
        if account.current_balance < settings.bank_alert_threshold:
            alerts.append(f'{account.name} balance is below threshold (M {settings.bank_alert_threshold})')

    context = {
        'settings': settings,
        'cash_balance': cash_balance,
        'bank_total': bank_total,
        'bank_accounts': bank_accounts,
        'recent_transactions': recent_transactions,
        'alerts': alerts,
    }
    return render(request, 'owner/cashbook/dashboard.html', context)


# ------------------------------------------------------------------
# Transaction ledger
# ------------------------------------------------------------------
@_owner_required
def cashbook_ledger(request):
    """Full transaction list with filters."""
    transactions = CashTransaction.objects.all()

    # Filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    t_type = request.GET.get('transaction_type')
    category = request.GET.get('category')

    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if t_type:
        transactions = transactions.filter(transaction_type=t_type)
    if category:
        transactions = transactions.filter(category=category)

    transactions = transactions.order_by('-date', '-created_at')

    # Summary
    total_additions = transactions.filter(
        transaction_type__in=['addition', 'transfer_from_bank', 'settlement_collection']
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_withdrawals = transactions.filter(
        transaction_type__in=['withdrawal', 'transfer_to_bank', 'expense_cash',
                              'petty_cash', 'salary_payment', 'commission_payment',
                              'bonus_payment', 'loan_repayment']
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'transactions': transactions,
        'start_date': start_date or '',
        'end_date': end_date or '',
        'total_additions': total_additions,
        'total_withdrawals': total_withdrawals,
        'net': total_additions - total_withdrawals,
    }
    return render(request, 'owner/cashbook/ledger.html', context)


# ------------------------------------------------------------------
# Transaction CRUD
# ------------------------------------------------------------------
@_owner_required
def cashbook_entries(request):
    """List all transactions (alias for ledger with different template)."""
    transactions = CashTransaction.objects.all().order_by('-date', '-created_at')
    return render(request, 'owner/cashbook/entries.html', {'transactions': transactions})


@_owner_required
def cashbook_add(request):
    """Record any transaction."""
    if request.method == 'POST':
        form = CashTransactionForm(request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            try:
                transaction.save()
                messages.success(request, 'Transaction recorded successfully.')
                return redirect('owner_cashbook_dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CashTransactionForm()
    return render(request, 'owner/cashbook/form.html', {
        'form': form,
        'title': 'Add Transaction',
        'cash_balance': CashInHand.get_balance(),
    })


@_owner_required
def cashbook_edit(request, transaction_id):
    """Edit a transaction (only if not a settlement collection)."""
    transaction = get_object_or_404(CashTransaction, id=transaction_id)

    if transaction.transaction_type == 'settlement_collection':
        messages.error(request, 'Settlement collection transactions cannot be edited.')
        return redirect('owner_cashbook_ledger')

    if request.method == 'POST':
        form = CashTransactionForm(request.POST, request.FILES, instance=transaction)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Transaction updated successfully.')
                return redirect('owner_cashbook_ledger')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CashTransactionForm(instance=transaction)

    return render(request, 'owner/cashbook/form.html', {
        'form': form,
        'title': 'Edit Transaction',
        'transaction': transaction,
        'cash_balance': CashInHand.get_balance(),
    })


@_owner_required
def cashbook_delete(request, transaction_id):
    """Delete a transaction."""
    transaction = get_object_or_404(CashTransaction, id=transaction_id)

    if transaction.transaction_type == 'settlement_collection':
        messages.error(request, 'Settlement collection transactions cannot be deleted.')
        return redirect('owner_cashbook_ledger')

    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted.')
        return redirect('owner_cashbook_ledger')

    return render(request, 'owner/cashbook/delete.html', {'transaction': transaction})


@_owner_required
def cashbook_export_csv(request):
    """Export all transactions to CSV."""
    import csv
    from django.http import HttpResponse

    transactions = CashTransaction.objects.all().order_by('-date', '-created_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="cashbook_ledger.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Bank Account',
                     'Cash Balance After', 'Bank Balance After', 'Reference', 'Notes'])
    for t in transactions:
        writer.writerow([
            t.date, t.get_transaction_type_display(), t.get_category_display(),
            t.amount, t.bank_account.name if t.bank_account else '-',
            t.cash_balance_after or '-', t.bank_balance_after or '-',
            t.reference or '-', t.notes or '-',
        ])
    return response


# ------------------------------------------------------------------
# Bank accounts
# ------------------------------------------------------------------
@_owner_required
def bank_list(request):
    accounts = BankAccount.objects.all().order_by('name')
    total_active = accounts.filter(is_active=True).aggregate(
        total=Sum('current_balance')
    )['total'] or 0
    return render(request, 'owner/cashbook/banks.html', {
        'accounts': accounts,
        'total_active': total_active,
    })


@_owner_required
def bank_add(request):
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank account added successfully.')
            return redirect('owner_cashbook_banks')
    else:
        form = BankAccountForm()
    return render(request, 'owner/cashbook/bank_form.html', {
        'form': form,
        'title': 'Add Bank Account',
    })


@_owner_required
def bank_edit(request, bank_id):
    account = get_object_or_404(BankAccount, id=bank_id)
    if request.method == 'POST':
        form = BankAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank account updated successfully.')
            return redirect('owner_cashbook_banks')
    else:
        form = BankAccountForm(instance=account)
    return render(request, 'owner/cashbook/bank_form.html', {
        'form': form,
        'title': 'Edit Bank Account',
        'account': account,
    })


@_owner_required
def bank_delete(request, bank_id):
    account = get_object_or_404(BankAccount, id=bank_id)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Bank account deleted.')
        return redirect('owner_cashbook_banks')
    return render(request, 'owner/cashbook/bank_delete.html', {'account': account})


# ------------------------------------------------------------------
# Transfers
# ------------------------------------------------------------------
@_owner_required
def bank_deposit(request):
    """Transfer cash to bank (deposit)."""
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.transaction_type = 'transfer_to_bank'
            transaction.category = 'other_income'
            transaction.created_by = request.user
            try:
                transaction.save()
                messages.success(request, f'Deposited M {transaction.amount} to {transaction.bank_account.name}.')
                return redirect('owner_cashbook_dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DepositForm()
    return render(request, 'owner/cashbook/deposit.html', {
        'form': form,
        'title': 'Deposit to Bank',
        'cash_in_hand': CashInHand.get_balance(),
    })


@_owner_required
def bank_withdraw(request):
    """Transfer from bank to cash (withdrawal)."""
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.transaction_type = 'transfer_from_bank'
            transaction.category = 'other_income'
            transaction.created_by = request.user
            try:
                transaction.save()
                messages.success(request, f'Withdrew M {transaction.amount} from {transaction.bank_account.name}.')
                return redirect('owner_cashbook_dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DepositForm()
    return render(request, 'owner/cashbook/withdraw.html', {
        'form': form,
        'title': 'Withdraw from Bank',
        'cash_in_hand': CashInHand.get_balance(),
    })


# ------------------------------------------------------------------
# Expenses
# ------------------------------------------------------------------
@_owner_required
def record_expense(request):
    """Record an expense (cash or bank)."""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            try:
                transaction.save()
                messages.success(request, 'Expense recorded successfully.')
                return redirect('owner_cashbook_dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExpenseForm()
    return render(request, 'owner/cashbook/expense.html', {
        'form': form,
        'title': 'Record Expense',
        'cash_in_hand': CashInHand.get_balance(),
    })


@_owner_required
def record_petty_cash(request):
    """Record a petty cash expense."""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.transaction_type = 'petty_cash'
            transaction.category = 'petty_cash_expense'
            transaction.created_by = request.user
            try:
                transaction.save()
                messages.success(request, 'Petty cash expense recorded.')
                return redirect('owner_cashbook_dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExpenseForm(initial={'transaction_type': 'petty_cash', 'category': 'petty_cash_expense'})
    return render(request, 'owner/cashbook/expense.html', {
        'form': form,
        'title': 'Record Petty Cash',
        'cash_in_hand': CashInHand.get_balance(),
    })