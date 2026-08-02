"""
Owner portal views for loan management.
All views require staff authentication (owner access).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime

from reports.views import _get_date_range
from .models import Loan, LoanPayment, LoanInterest
from drivers.models import Driver
from cashbook.models import BankAccount, CashTransaction, CashInHand


def is_owner(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_owner)
def loan_report(request):
    """Loan report with outstanding balances and interest."""
    start_date, end_date = _get_date_range(request)
    status_filter = request.GET.get('status', '')

    loans = Loan.objects.all().order_by('-start_date')
    if status_filter:
        loans = loans.filter(status=status_filter)

    total_outstanding = loans.filter(status='active').aggregate(
        total=Sum('outstanding_balance')
    )['total'] or 0

    total_paid = LoanPayment.objects.filter(
        date__gte=start_date, date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_interest = LoanInterest.objects.filter(
        date__gte=start_date, date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'loans': loans,
        'total_outstanding': total_outstanding,
        'total_paid': total_paid,
        'total_interest': total_interest,
        'start_date': start_date,
        'end_date': end_date,
        'status_choices': Loan.STATUS_CHOICES,
        'current_status': status_filter,
    }
    return render(request, 'reports/loan_report.html', context)


@login_required
@user_passes_test(is_owner)
def loan_list(request):
    """List all loans."""
    status_filter = request.GET.get('status', 'active')
    loan_type_filter = request.GET.get('type', '')

    loans = Loan.objects.all()
    if status_filter:
        loans = loans.filter(status=status_filter)
    if loan_type_filter:
        loans = loans.filter(loan_type=loan_type_filter)

    total_outstanding = loans.filter(status='active').aggregate(
        total=Sum('outstanding_balance')
    )['total'] or 0

    context = {
        'loans': loans,
        'total_outstanding': total_outstanding,
        'status_choices': Loan.STATUS_CHOICES,
        'type_choices': Loan.LOAN_TYPES,
        'current_status': status_filter,
        'current_type': loan_type_filter,
    }
    return render(request, 'owner/loans/list.html', context)


@login_required
@user_passes_test(is_owner)
def loan_add(request):
    """Add a new loan."""
    if request.method == 'POST':
        loan_type = request.POST.get('loan_type')
        driver_id = request.POST.get('driver') or None
        amount = Decimal(request.POST.get('amount', '0'))
        interest_rate = Decimal(request.POST.get('interest_rate', '0'))
        interest_method = request.POST.get('interest_method', 'simple')
        interest_frequency = request.POST.get('interest_frequency', 'monthly')
        start_date = request.POST.get('start_date')
        expected_repayment_date = request.POST.get('expected_repayment_date') or None
        purpose = request.POST.get('purpose', '')
        notes = request.POST.get('notes', '')

        loan = Loan(
            loan_type=loan_type,
            driver_id=driver_id,
            amount=amount,
            outstanding_balance=amount,
            interest_rate=interest_rate,
            interest_method=interest_method,
            interest_frequency=interest_frequency,
            start_date=start_date,
            expected_repayment_date=expected_repayment_date,
            purpose=purpose,
            notes=notes,
        )
        loan.save()

        # --- Determine transaction type and validate cash for driver loans ---
        if loan_type == 'business':
            transaction_type = 'addition'
        else:
            # Driver loan – check cash availability
            cash_balance = CashInHand.get_balance()
            if amount > cash_balance:
                messages.error(
                    request,
                    f"Insufficient cash to disburse this driver loan. "
                    f"Cash in hand: M {cash_balance:.2f}, Loan amount: M {amount:.2f}"
                )
                loan.delete()  # remove the loan record
                return redirect('loans:loan_add')
            transaction_type = 'withdrawal'

        # Create cash transaction – this will update CashInHand automatically
        CashTransaction.objects.create(
            transaction_type=transaction_type,
            category='loan_disbursement',
            amount=amount,
            date=timezone.now().date(),
            notes=f"Loan disbursement - {loan.get_loan_type_display()}",
            loan=loan,
        )

        messages.success(request, f'Loan of M {amount} created successfully.')
        return redirect('loans:loan_list')

    context = {
        'drivers': Driver.objects.filter(is_active=True),
        'bank_accounts': BankAccount.objects.filter(is_active=True),
        'interest_methods': Loan.INTEREST_METHODS,
        'interest_frequencies': Loan.FREQUENCY_CHOICES,
        'loan_types': Loan.LOAN_TYPES,
        'today': timezone.now().date(),
    }
    return render(request, 'owner/loans/form.html', context)


@login_required
@user_passes_test(is_owner)
def loan_detail(request, loan_id):
    """Loan details with payments and interest history."""
    loan = get_object_or_404(Loan, id=loan_id)
    payments = loan.payments.all().order_by('-date')
    interest_entries = loan.interest_entries.all().order_by('-date')

    interest_projection = loan.calculate_interest()

    context = {
        'loan': loan,
        'payments': payments,
        'interest_entries': interest_entries,
        'interest_projection': interest_projection,
        'total_paid': loan.total_paid,
        'total_interest': loan.total_interest_accrued,
    }
    return render(request, 'owner/loans/detail.html', context)


@login_required
@user_passes_test(is_owner)
def loan_pay(request, loan_id):
    """Record a loan payment."""
    loan = get_object_or_404(Loan, id=loan_id)

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        payment_method = request.POST.get('payment_method')
        date = request.POST.get('date')
        reference = request.POST.get('reference', '')
        notes = request.POST.get('notes', '')
        bank_account_id = request.POST.get('bank_account') or None

        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('loans:loan_pay', loan_id=loan.id)

        if amount > loan.outstanding_balance:
            messages.error(request, f'Amount exceeds outstanding balance of M {loan.outstanding_balance}.')
            return redirect('loans:loan_pay', loan_id=loan.id)

        # For cash/bank payments, ensure bank account is selected if method is bank
        if payment_method == 'bank' and not bank_account_id:
            messages.error(request, 'Please select a bank account for bank transfers.')
            context = {
                'loan': loan,
                'payment_methods': LoanPayment.PAYMENT_METHODS,
                'bank_accounts': BankAccount.objects.filter(is_active=True),
            }
            return render(request, 'owner/loans/pay.html', context)

        payment = LoanPayment(
            loan=loan,
            amount=amount,
            date=date,
            payment_method=payment_method,
            reference=reference,
            notes=notes,
        )

        if bank_account_id:
            payment.bank_account_id = bank_account_id

        try:
            payment.save()
            messages.success(request, f'Payment of M {amount} recorded successfully.')
            return redirect('loans:loan_detail', loan_id=loan.id)
        except ValidationError as e:
            messages.error(request, str(e))
            context = {
                'loan': loan,
                'payment_methods': LoanPayment.PAYMENT_METHODS,
                'bank_accounts': BankAccount.objects.filter(is_active=True),
            }
            return render(request, 'owner/loans/pay.html', context)

    context = {
        'loan': loan,
        'payment_methods': LoanPayment.PAYMENT_METHODS,
        'bank_accounts': BankAccount.objects.filter(is_active=True),
    }
    return render(request, 'owner/loans/pay.html', context)


@login_required
@user_passes_test(is_owner)
def loan_accrue_interest(request, loan_id):
    """Manually accrue interest for a loan."""
    loan = get_object_or_404(Loan, id=loan_id)

    if request.method == 'POST':
        as_of_date_str = request.POST.get('as_of_date')
        if as_of_date_str:
            try:
                as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
            except ValueError:
                as_of_date = timezone.now().date()
        else:
            as_of_date = timezone.now().date()

        loan.accrue_interest(as_of_date)
        messages.success(request, f'Interest accrued up to {as_of_date}.')
        return redirect('loans:loan_detail', loan_id=loan.id)

    context = {
        'loan': loan,
        'projected_interest': loan.calculate_interest(),
        'today': timezone.now().date(),
    }
    return render(request, 'owner/loans/accrue_interest.html', context)