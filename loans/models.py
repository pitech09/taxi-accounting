from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime
from drivers.models import Driver
from cashbook.models import CashTransaction, CashInHand, BankAccount


class Loan(models.Model):
    LOAN_TYPES = [
        ('driver', 'Driver Advance'),
        ('business', 'Business Loan'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paid', 'Paid Off'),
        ('defaulted', 'Defaulted'),
    ]
    INTEREST_METHODS = [
        ('simple', 'Simple Interest'),
        ('compound', 'Compound Interest'),
        ('flat', 'Flat Rate'),
        ('none', 'No Interest'),
    ]
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]

    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='loans')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    interest_method = models.CharField(max_length=20, choices=INTEREST_METHODS, default='simple')
    interest_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    start_date = models.DateField()
    expected_repayment_date = models.DateField(null=True, blank=True)
    last_interest_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    purpose = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_loan_type_display()} - M {self.amount} ({self.status})"

    @property
    def total_paid(self):
        return self.payments.aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def total_interest_accrued(self):
        return self.interest_entries.aggregate(total=models.Sum('amount'))['total'] or 0

    def _parse_date(self, value):
        if value is None:
            return timezone.now().date()
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return timezone.now().date()
        return value

    def calculate_interest(self, as_of_date=None):
        as_of_date = self._parse_date(as_of_date)
        if self.interest_rate == 0 or self.status != 'active':
            return Decimal('0.00')
        
        start_date = self.last_interest_date or self.start_date
        days = (as_of_date - start_date).days
        if days <= 0:
            return Decimal('0.00')
        
        days_dec = Decimal(str(days))
        rate = self.interest_rate / Decimal('100')
        daily_rate = rate / Decimal('365')
        
        if self.interest_method == 'simple':
            interest = self.outstanding_balance * daily_rate * days_dec
        elif self.interest_method == 'compound':
            rate_per_day = Decimal('1') + daily_rate
            interest = self.outstanding_balance * (rate_per_day ** days_dec) - self.outstanding_balance
        elif self.interest_method == 'flat':
            flat_rate = rate
            interest = self.amount * flat_rate * (days_dec / Decimal('365'))
        else:
            return Decimal('0.00')
        
        return interest.quantize(Decimal('0.01'))

    def accrue_interest(self, as_of_date=None):
        as_of_date = self._parse_date(as_of_date)
        amount = self.calculate_interest(as_of_date)
        if amount <= 0:
            return
        LoanInterest.objects.create(loan=self, amount=amount, date=as_of_date)
        self.last_interest_date = as_of_date
        self.save(update_fields=['last_interest_date'])

    def update_balance(self):
        total_paid = self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        total_interest = self.interest_entries.aggregate(total=models.Sum('amount'))['total'] or 0
        self.outstanding_balance = self.amount + total_interest - total_paid
        if self.outstanding_balance <= 0:
            self.status = 'paid'
            self.outstanding_balance = 0
        self.save()

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['driver', 'status']), models.Index(fields=['status'])]


class LoanPayment(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('settlement', 'Settlement Deduction'),
        ('driver_pay', 'Driver Pay Deduction'),
    ]
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    settlement = models.ForeignKey('settlements.DailySettlement', on_delete=models.SET_NULL, null=True, blank=True)
    bank_account = models.ForeignKey('cashbook.BankAccount', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 1. For cash/bank payments, create CashTransaction FIRST to validate funds
        if self.payment_method in ['cash', 'bank']:
            CashTransaction.objects.create(
                transaction_type='expense_cash' if self.payment_method == 'cash' else 'expense_bank',
                category='loan_repayment',
                amount=self.amount,
                date=self.date,
                bank_account=self.bank_account,
                loan=self.loan,
                notes=f"Loan repayment for {self.loan.get_loan_type_display()} - {self.notes}",
            )

        # 2. Save the payment (this updates loan balance via update_balance)
        super().save(*args, **kwargs)

        # 3. Update loan balance (redundant if super save calls it, but safe)
        self.loan.update_balance()


class LoanInterest(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='interest_entries')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.loan.update_balance()