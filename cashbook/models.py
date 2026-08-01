"""
Cash book models for the Taxi Accounting System.

CashInHand  – singleton tracking physical cash balance.
BankAccount – tracks individual bank account balances.
CashTransaction – every cash/bank movement (income, expense, transfer, settlement).
DailyCashBook – daily summary of cash in/out.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone


def _round2(value):
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    if value is None:
        return Decimal('0.00')
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class CashInHand(models.Model):
    """Singleton model tracking the physical cash balance."""

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cash in Hand'
        verbose_name_plural = 'Cash in Hand'

    def __str__(self):
        return f"Cash in Hand: M {self.balance}"

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    @classmethod
    def get_balance(cls):
        return cls.get_instance().balance

    @classmethod
    def add(cls, amount, transaction=None):
        instance = cls.get_instance()
        instance.balance = _round2(instance.balance + amount)
        instance.save()
        return instance.balance

    @classmethod
    def subtract(cls, amount, transaction=None):
        instance = cls.get_instance()
        instance.balance = _round2(instance.balance - amount)
        instance.save()
        return instance.balance


class BankAccount(models.Model):
    name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.bank_name})"

    def add_balance(self, amount):
        self.current_balance = _round2(self.current_balance + amount)
        self.save()
        return self.current_balance

    def subtract_balance(self, amount):
        self.current_balance = _round2(self.current_balance - amount)
        self.save()
        return self.current_balance

    def save(self, *args, **kwargs):
        if not self.pk:
            self.current_balance = _round2(self.opening_balance)
        super().save(*args, **kwargs)


class CashTransaction(models.Model):
    """A single cash or bank transaction."""

    TRANSACTION_TYPES = [
        ('addition', 'Cash Addition'),
        ('withdrawal', 'Cash Withdrawal'),
        ('transfer_to_bank', 'Transfer to Bank'),
        ('transfer_from_bank', 'Transfer from Bank'),
        ('expense_cash', 'Expense (Cash)'),
        ('expense_bank', 'Expense (Bank)'),
        ('petty_cash', 'Petty Cash'),
        ('salary_payment', 'Salary Payment'),
        ('commission_payment', 'Commission Payment'),
        ('bonus_payment', 'Bonus Payment'),
        # Loan-specific types
        ('loan_disbursement', 'Loan Disbursement'),
        ('loan_repayment', 'Loan Repayment'),
        ('loan_interest', 'Loan Interest'),
        ('settlement_collection', 'Settlement Collection'),
    ]

    CATEGORY_CHOICES = [
        ('settlement_collection', 'Driver Settlement Collection'),
        ('other_income', 'Other Income'),
        ('loan_income', 'Loan Received'),
        ('loan_disbursement', 'Loan Disbursement'),
        ('loan_repayment', 'Loan Repayment'),
        ('loan_interest', 'Loan Interest'),
        ('fuel', 'Fuel'),
        ('maintenance', 'Maintenance/Repairs'),
        ('insurance', 'Insurance'),
        ('permit', 'Permit/License'),
        ('admin_expense', 'Admin Expense'),
        ('driver_salary', 'Driver Salary'),
        ('driver_commission', 'Driver Commission'),
        ('driver_bonus', 'Driver Bonus'),
        ('other_expense', 'Other Expense'),
        ('petty_cash_expense', 'Petty Cash Expense'),
    ]

    settlement = models.ForeignKey(
        'settlements.DailySettlement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_transactions',
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
    )
    # Optional link to a loan (for loan-related transactions)
    loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_transactions',
    )

    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    reference = models.CharField(max_length=100, blank=True)
    receipt_photo = models.ImageField(upload_to='receipts/', null=True, blank=True)

    cash_balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False, null=True, blank=True
    )
    bank_balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False, null=True, blank=True
    )

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_transactions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - M {self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        """
        Update CashInHand and/or BankAccount balances based on transaction type,
        and store the resulting balances in cash_balance_after / bank_balance_after.
        """
        is_new = self.pk is None

        if is_new:
            # Determine which cash movements to apply
            additions = ('addition', 'transfer_from_bank', 'settlement_collection')
            subtractions = ('withdrawal', 'transfer_to_bank', 'expense_cash',
                           'petty_cash', 'salary_payment', 'commission_payment',
                           'bonus_payment', 'loan_repayment', 'loan_disbursement')

            if self.transaction_type in additions:
                CashInHand.add(self.amount, self)
            elif self.transaction_type in subtractions:
                CashInHand.subtract(self.amount, self)

            # Bank movements
            if self.transaction_type == 'transfer_to_bank' and self.bank_account:
                self.bank_account.add_balance(self.amount)
            elif self.transaction_type == 'transfer_from_bank' and self.bank_account:
                self.bank_account.subtract_balance(self.amount)
            elif self.transaction_type == 'expense_bank' and self.bank_account:
                self.bank_account.subtract_balance(self.amount)

            # Store resulting balances
            self.cash_balance_after = CashInHand.get_balance()
            self.bank_balance_after = self.bank_account.current_balance if self.bank_account else None

        super().save(*args, **kwargs)


class DailyCashBook(models.Model):
    """Daily summary of cash in/out for the cash book."""

    date = models.DateField(unique=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cash_in = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cash_out = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Cash Book - {self.date}"

    @property
    def net_cash_flow(self):
        return _round2(self.total_cash_in - self.total_cash_out)