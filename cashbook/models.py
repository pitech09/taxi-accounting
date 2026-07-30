from decimal import Decimal
from django.db import models
from django.utils import timezone


class CashInHand(models.Model):
    """Singleton model to store current cash balance."""
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cash in Hand: M {self.balance:.2f}"

    @classmethod
    def get_balance(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj.balance

    @classmethod
    def add(cls, amount, transaction=None):
        obj, _ = cls.objects.get_or_create(id=1)
        obj.balance += amount
        obj.save()

    @classmethod
    def subtract(cls, amount, transaction=None):
        obj, _ = cls.objects.get_or_create(id=1)
        obj.balance -= amount
        obj.save()


class BankAccount(models.Model):
    name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.bank_name})"


class CashTransaction(models.Model):
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
        ('loan_repayment', 'Loan Repayment'),
        ('settlement_collection', 'Settlement Collection'),
    ]

    CATEGORY_CHOICES = [
        ('settlement_collection', 'Driver Settlement Collection'),
        ('other_income', 'Other Income'),
        ('loan_income', 'Loan Received'),
        ('fuel', 'Fuel'),
        ('maintenance', 'Maintenance/Repairs'),
        ('insurance', 'Insurance'),
        ('permit', 'Permit/License'),
        ('admin_expense', 'Admin Expense'),
        ('driver_salary', 'Driver Salary'),
        ('driver_commission', 'Driver Commission'),
        ('driver_bonus', 'Driver Bonus'),
        ('repayment', 'Loan Repayment'),
        ('other_expense', 'Other Expense'),
        ('petty_cash_expense', 'Petty Cash Expense'),
    ]

    # Relations
    settlement = models.ForeignKey(
        'settlements.DailySettlement',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cash_transactions'
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transactions'
    )

    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()

    reference = models.CharField(max_length=100, blank=True)
    receipt_photo = models.ImageField(upload_to='receipts/', null=True, blank=True)

    # Running balances (calculated on save)
    cash_balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False, null=True, blank=True
    )
    bank_balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False, null=True, blank=True
    )

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - M {self.amount:.2f} ({self.date})"

    def _d(self, value):
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    def save(self, *args, **kwargs):
        self.amount = self._d(self.amount)
        is_new = self.pk is None

        # Determine if this transaction affects cash in hand or bank
        cash_increase_types = ['addition', 'transfer_from_bank', 'settlement_collection']
        cash_decrease_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash',
                               'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']
        bank_increase_types = ['transfer_from_bank']
        bank_decrease_types = ['transfer_to_bank', 'expense_bank']

        # If editing, reverse previous effects first
        if not is_new:
            old = CashTransaction.objects.get(pk=self.pk)
            self._reverse_previous_effect(old)

        # Save the transaction first
        super().save(*args, **kwargs)

        # Update Cash in Hand
        if self.transaction_type in cash_increase_types:
            CashInHand.add(self.amount, self)
        elif self.transaction_type in cash_decrease_types:
            CashInHand.subtract(self.amount, self)
        self.cash_balance_after = CashInHand.get_balance()

        # Update Bank balance
        if self.bank_account:
            if self.transaction_type in bank_increase_types:
                self.bank_account.current_balance += self.amount
            elif self.transaction_type in bank_decrease_types:
                self.bank_account.current_balance -= self.amount
            self.bank_account.save()
            self.bank_balance_after = self.bank_account.current_balance

        # Update computed fields without re-triggering save
        CashTransaction.objects.filter(pk=self.pk).update(
            cash_balance_after=self.cash_balance_after,
            bank_balance_after=self.bank_balance_after,
        )

    def delete(self, *args, **kwargs):
        # Reverse effects before deleting
        cash_increase_types = ['addition', 'transfer_from_bank', 'settlement_collection']
        cash_decrease_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash',
                               'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']
        bank_increase_types = ['transfer_from_bank']
        bank_decrease_types = ['transfer_to_bank', 'expense_bank']

        if self.transaction_type in cash_increase_types:
            CashInHand.subtract(self.amount, self)
        elif self.transaction_type in cash_decrease_types:
            CashInHand.add(self.amount, self)

        if self.bank_account:
            if self.transaction_type in bank_increase_types:
                self.bank_account.current_balance -= self.amount
            elif self.transaction_type in bank_decrease_types:
                self.bank_account.current_balance += self.amount
            self.bank_account.save()

        super().delete(*args, **kwargs)

    def _reverse_previous_effect(self, old):
        """Reverse the effect of the previous version of this transaction."""
        cash_increase_types = ['addition', 'transfer_from_bank', 'settlement_collection']
        cash_decrease_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash',
                               'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']
        bank_increase_types = ['transfer_from_bank']
        bank_decrease_types = ['transfer_to_bank', 'expense_bank']

        if old.transaction_type in cash_increase_types:
            CashInHand.subtract(old.amount, old)
        elif old.transaction_type in cash_decrease_types:
            CashInHand.add(old.amount, old)

        if old.bank_account:
            if old.transaction_type in bank_increase_types:
                old.bank_account.current_balance -= old.amount
            elif old.transaction_type in bank_decrease_types:
                old.bank_account.current_balance += old.amount
            old.bank_account.save()

    @property
    def is_inflow(self):
        """Whether this transaction increases cash in hand."""
        return self.transaction_type in ['addition', 'transfer_from_bank', 'settlement_collection']

    @property
    def is_outflow(self):
        """Whether this transaction decreases cash in hand."""
        return self.transaction_type in [
            'withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash',
            'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment'
        ]

    @property
    def affects_cash(self):
        return self.transaction_type in [
            'addition', 'withdrawal', 'transfer_to_bank', 'transfer_from_bank',
            'expense_cash', 'petty_cash', 'settlement_collection',
            'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment'
        ]

    @property
    def affects_bank(self):
        return self.transaction_type in ['transfer_to_bank', 'transfer_from_bank', 'expense_bank']


class DailyCashBook(models.Model):
    date = models.DateField(unique=True)

    # Cash movements
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cash_in = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cash_out = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Bank movements
    total_bank_deposits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_bank_withdrawals = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bank_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Summary
    total_settlement_collections = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_vehicle_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_driver_payments = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_business_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_cash_flow = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cash Book - {self.date}"

    def calculate_totals(self):
        """Recalculate totals from transactions."""
        from django.db.models import Sum

        cash_in_types = ['addition', 'transfer_from_bank', 'settlement_collection']
        cash_out_types = ['withdrawal', 'transfer_to_bank', 'expense_cash', 'petty_cash',
                          'salary_payment', 'commission_payment', 'bonus_payment', 'loan_repayment']

        cash_in = CashTransaction.objects.filter(
            date=self.date,
            transaction_type__in=cash_in_types
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        cash_out = CashTransaction.objects.filter(
            date=self.date,
            transaction_type__in=cash_out_types
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        self.total_cash_in = cash_in
        self.total_cash_out = cash_out
        self.closing_balance = self.opening_balance + cash_in - cash_out

        self.total_bank_deposits = CashTransaction.objects.filter(
            date=self.date, transaction_type='transfer_to_bank'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        self.total_bank_withdrawals = CashTransaction.objects.filter(
            date=self.date, transaction_type='transfer_from_bank'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        self.total_settlement_collections = CashTransaction.objects.filter(
            date=self.date, category='settlement_collection'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        self.total_vehicle_expenses = CashTransaction.objects.filter(
            date=self.date, category__in=['fuel', 'maintenance', 'insurance', 'permit']
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        self.total_driver_payments = CashTransaction.objects.filter(
            date=self.date, category__in=['driver_salary', 'driver_commission', 'driver_bonus']
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        self.total_business_expenses = CashTransaction.objects.filter(
            date=self.date, transaction_type__in=['expense_cash', 'expense_bank', 'petty_cash']
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        self.net_cash_flow = cash_in - cash_out

        self.save()