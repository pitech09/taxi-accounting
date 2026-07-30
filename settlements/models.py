from decimal import Decimal
from django.db import models
from django.utils import timezone
from vehicles.models import Vehicle
from drivers.models import Driver


class DailySettlement(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('ecocash', 'EcoCash'),
        ('card', 'Card'),
        ('mixed', 'Mixed'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ]

    # Relations
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='settlements')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='settlements')
    date = models.DateField()  # changed from auto_now_add to allow driver entry

    # INCOME (Pure accounting)
    cash_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mobile_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    card_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    advance_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # EXPENSES (paid by owner)
    fuel_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    toll_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    border_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    repair_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    driver_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # CALCULATIONS (auto-calculated on approval)
    total_income = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    total_expenses = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    gross_profit = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)

    # Operating model specific fields
    operating_model = models.CharField(max_length=20, choices=Vehicle.OPERATING_MODELS, editable=False, default='quota')

    # QUOTA SYSTEM FIELDS
    daily_quota = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    surplus_shortfall = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    previous_debt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    debt_repaid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_debt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quota_paid_to_owner = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # SALARY SYSTEM FIELDS
    daily_salary_earned = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    monthly_salary_accumulated = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # PERCENTAGE SYSTEM FIELDS
    driver_percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False, default=0)
    driver_percentage_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    owner_percentage_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)

    # CONTRACT SYSTEM FIELDS
    contract_target = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    contract_monthly_gross = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    contract_remaining_target = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    contract_driver_bonus = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    contract_driver_failure_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    contract_is_success = models.BooleanField(editable=False, default=False)
    contract_bonus_type = models.CharField(max_length=20, editable=False, default='')
    contract_success_bonus_fixed = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    contract_success_bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False, default=0)
    contract_failure_percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False, default=0)
    contract_driver_pay = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    contract_owner_pay = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)

    # DRIVER COMPENSATION (generic)
    driver_pay = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)

    # PAYMENTS (generic)
    total_owner_collected = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)

    # Cash book integration
    cash_added_to_hand = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    cash_transaction_created = models.BooleanField(default=False)

    # METADATA
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='mixed')
    notes = models.TextField(blank=True)

    # STATUS
    debt_status = models.CharField(max_length=20, choices=[
        ('clear', 'Clear'),
        ('owing', 'Owing'),
        ('overdue', 'Overdue'),
        ('n/a', 'Not Applicable'),
    ], default='n/a')

    # ── Approval workflow fields ──────────────────────────────────
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    settlement_period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='daily')
    week_start = models.DateField(null=True, blank=True)
    week_end = models.DateField(null=True, blank=True)
    driver_notes = models.TextField(blank=True)
    owner_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_settlements'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['vehicle', 'driver', 'date']

    def __str__(self):
        period = f"{self.week_start}–{self.week_end}" if self.settlement_period == 'weekly' else str(self.date)
        return f"{self.driver.name} – {period} ({self.get_status_display()})"

    def _d(self, value):
        """Convert a value to Decimal safely"""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @property
    def period_display(self):
        if self.settlement_period == 'weekly':
            return f"{self.week_start} to {self.week_end}" if self.week_start and self.week_end else "Weekly"
        return str(self.date)

    @property
    def is_calculated(self):
        """Whether model calculations have been applied (approved)."""
        return self.status == 'approved'

    def save(self, *args, **kwargs):
        # Ensure date is set
        if not self.date:
            self.date = timezone.now().date()

        # Convert all numeric fields to Decimal
        self.cash_collected = self._d(self.cash_collected)
        self.mobile_collected = self._d(self.mobile_collected)
        self.card_collected = self._d(self.card_collected)
        self.advance_income = self._d(self.advance_income)
        self.other_income = self._d(self.other_income)
        self.fuel_cost = self._d(self.fuel_cost)
        self.toll_cost = self._d(self.toll_cost)
        self.border_fee = self._d(self.border_fee)
        self.repair_cost = self._d(self.repair_cost)
        self.driver_allowance = self._d(self.driver_allowance)
        self.other_expenses = self._d(self.other_expenses)

        # Always compute income/expenses/gross profit (useful for display even before approval)
        self.total_income = (
            self.cash_collected + self.mobile_collected +
            self.card_collected + self.advance_income + self.other_income
        )
        self.total_expenses = (
            self.fuel_cost + self.toll_cost + self.border_fee +
            self.repair_cost + self.driver_allowance + self.other_expenses
        )
        self.gross_profit = self.total_income - self.total_expenses

        # Get vehicle operating model
        self.operating_model = self.vehicle.operating_model if self.vehicle else self.operating_model

        # Only run model calculations when status is 'approved'
        if self.status == 'approved':
            self._run_model_calculations()
        else:
            # Reset calculated fields for non-approved states
            self._reset_calculation_fields()

        super().save(*args, **kwargs)

        # Cash book integration: create cash transaction when approved
        if self.status == 'approved' and not self.cash_transaction_created and self.total_owner_collected > 0:
            self._create_cash_transaction()

    def _create_cash_transaction(self):
        """Create a cash transaction for the owner collection when settlement is approved."""
        from cashbook.models import CashTransaction

        self.cash_added_to_hand = self.total_owner_collected
        CashTransaction.objects.create(
            settlement=self,
            transaction_type='addition',
            category='settlement_collection',
            amount=self.total_owner_collected,
            date=self.date,
            notes=f"Collection from {self.driver.name} - {self.get_operating_model_display()}",
            created_by=self.approved_by,
        )
        self.cash_transaction_created = True
        # Update without re-triggering save logic
        DailySettlement.objects.filter(pk=self.pk).update(
            cash_added_to_hand=self.cash_added_to_hand,
            cash_transaction_created=self.cash_transaction_created,
        )

    def _reset_calculation_fields(self):
        """Reset model-specific calculated fields to zero for non-approved states."""
        self.daily_quota = Decimal('0')
        self.surplus_shortfall = Decimal('0')
        self.previous_debt = Decimal('0')
        self.debt_repaid = Decimal('0')
        self.new_debt = Decimal('0')
        self.quota_paid_to_owner = Decimal('0')
        self.daily_salary_earned = Decimal('0')
        self.monthly_salary_accumulated = Decimal('0')
        self.driver_percentage = Decimal('0')
        self.driver_percentage_amount = Decimal('0')
        self.owner_percentage_amount = Decimal('0')
        self.contract_target = Decimal('0')
        self.contract_monthly_gross = Decimal('0')
        self.contract_remaining_target = Decimal('0')
        self.contract_driver_bonus = Decimal('0')
        self.contract_driver_failure_amount = Decimal('0')
        self.contract_is_success = False
        self.contract_driver_pay = Decimal('0')
        self.contract_owner_pay = Decimal('0')
        self.driver_pay = Decimal('0')
        self.total_owner_collected = Decimal('0')
        self.debt_status = 'n/a'

    def _run_model_calculations(self):
        """Run the appropriate model calculations."""
        if self.operating_model == 'quota':
            self._process_quota_model()
        elif self.operating_model == 'salary':
            self._process_salary_model()
        elif self.operating_model == 'percentage':
            self._process_percentage_model()
        elif self.operating_model == 'contract':
            self._process_contract_model()

    def _process_quota_model(self):
        """Handle quota system calculations"""
        self.daily_quota = self._d(self.driver.effective_quota)
        self.surplus_shortfall = self.gross_profit - self.daily_quota

        previous_settlement = DailySettlement.objects.filter(
            driver=self.driver, status='approved'
        ).exclude(id=self.id).order_by('-date').first()
        self.previous_debt = self._d(previous_settlement.new_debt if previous_settlement else 0)

        if self.surplus_shortfall >= 0:
            self.debt_repaid = min(self.previous_debt, self.surplus_shortfall)
            self.new_debt = self.previous_debt - self.debt_repaid
            self.driver_pay = self.surplus_shortfall - self.debt_repaid
        else:
            self.debt_repaid = Decimal('0')
            self.new_debt = self.previous_debt + abs(self.surplus_shortfall)
            self.driver_pay = Decimal('0')

        self.quota_paid_to_owner = self.daily_quota if self.gross_profit >= self.daily_quota else self.gross_profit
        self.total_owner_collected = self.quota_paid_to_owner + self.debt_repaid

        if self.new_debt == 0:
            self.debt_status = 'clear'
        elif self.new_debt > 500:
            self.debt_status = 'overdue'
        else:
            self.debt_status = 'owing'

        self._clear_other_model_fields()

    def _process_salary_model(self):
        """Handle monthly salary system calculations"""
        monthly_salary = self._d(self.driver.effective_salary)
        days_in_month = Decimal('30')

        self.daily_salary_earned = monthly_salary / days_in_month

        month_start = self.date.replace(day=1)
        month_settlements = DailySettlement.objects.filter(
            driver=self.driver,
            date__gte=month_start,
            date__lte=self.date,
            operating_model='salary',
            status='approved'
        )

        total_salary_accumulated = sum((self._d(s.daily_salary_earned) for s in month_settlements), Decimal('0'))
        self.monthly_salary_accumulated = total_salary_accumulated

        self.driver_pay = self.daily_salary_earned
        self.total_owner_collected = self.gross_profit - self.driver_pay

        self.debt_status = 'n/a'
        self._clear_other_model_fields()

    def _process_percentage_model(self):
        """Handle percentage/commission system calculations"""
        self.driver_percentage = self._d(self.driver.effective_percentage)
        self.driver_percentage_amount = (self.driver_percentage / Decimal('100')) * self.total_income
        self.owner_percentage_amount = self.total_income - self.driver_percentage_amount

        self.driver_pay = self.driver_percentage_amount
        self.total_owner_collected = self.owner_percentage_amount

        self.debt_status = 'n/a'
        self._clear_other_model_fields()

    def _process_contract_model(self):
        """Handle contract/target system calculations"""
        target = self._d(self.driver.effective_contract_target)
        success_bonus_fixed = self._d(self.driver.effective_contract_success_bonus_fixed)
        success_bonus_percentage = self._d(self.driver.effective_contract_success_bonus_percentage)
        failure_percentage = self._d(self.driver.effective_contract_failure_percentage)

        month_start = self.date.replace(day=1)
        month_settlements = DailySettlement.objects.filter(
            driver=self.driver,
            date__gte=month_start,
            date__lte=self.date,
            operating_model='contract',
            status='approved'
        )

        monthly_gross = sum((self._d(s.total_income) for s in month_settlements), Decimal('0')) + self.total_income

        self.contract_target = target
        self.contract_monthly_gross = monthly_gross
        self.contract_remaining_target = max(Decimal('0'), target - monthly_gross)

        if monthly_gross >= target:
            self.contract_is_success = True
            self.contract_bonus_type = self.vehicle.contract_success_bonus_type if self.vehicle else 'fixed'
            self.contract_success_bonus_fixed = success_bonus_fixed
            self.contract_success_bonus_percentage = success_bonus_percentage

            if self.vehicle and self.vehicle.contract_success_bonus_type == 'fixed':
                self.contract_driver_bonus = success_bonus_fixed
            elif self.vehicle and self.vehicle.contract_success_bonus_type == 'percentage':
                self.contract_driver_bonus = (success_bonus_percentage / Decimal('100')) * monthly_gross
            else:
                self.contract_driver_bonus = success_bonus_fixed + ((success_bonus_percentage / Decimal('100')) * monthly_gross)

            self.contract_driver_failure_amount = Decimal('0')
        else:
            self.contract_is_success = False
            self.contract_failure_percentage = failure_percentage
            self.contract_driver_failure_amount = (failure_percentage / Decimal('100')) * monthly_gross
            self.contract_driver_bonus = Decimal('0')

        if self.contract_is_success:
            settlement_count = max(len(month_settlements), 1)
            self.contract_driver_pay = self.contract_driver_bonus / Decimal(str(settlement_count))
            self.contract_owner_pay = self.total_income - self.contract_driver_pay
        else:
            self.contract_driver_pay = (failure_percentage / Decimal('100')) * self.total_income
            self.contract_owner_pay = self.total_income - self.contract_driver_pay

        self.driver_pay = self.contract_driver_pay
        self.total_owner_collected = self.contract_owner_pay

        self.debt_status = 'n/a'
        self._clear_other_model_fields()

    def _clear_other_model_fields(self):
        """Clear fields not used by current model"""
        if self.operating_model != 'quota':
            self.daily_quota = Decimal('0')
            self.surplus_shortfall = Decimal('0')
            self.previous_debt = Decimal('0')
            self.debt_repaid = Decimal('0')
            self.new_debt = Decimal('0')
            self.quota_paid_to_owner = Decimal('0')

        if self.operating_model != 'salary':
            self.daily_salary_earned = Decimal('0')
            self.monthly_salary_accumulated = Decimal('0')

        if self.operating_model != 'percentage':
            self.driver_percentage = Decimal('0')
            self.driver_percentage_amount = Decimal('0')
            self.owner_percentage_amount = Decimal('0')

        if self.operating_model != 'contract':
            self.contract_target = Decimal('0')
            self.contract_monthly_gross = Decimal('0')
            self.contract_remaining_target = Decimal('0')
            self.contract_driver_bonus = Decimal('0')
            self.contract_driver_failure_amount = Decimal('0')
            self.contract_is_success = False
            self.contract_driver_pay = Decimal('0')
            self.contract_owner_pay = Decimal('0')


class DriverSettlementSchedule(models.Model):
    """Optional model for tracking driver settlement schedules over time."""
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='schedules')
    frequency = models.CharField(max_length=10, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ])
    week_start_day = models.IntegerField(default=0, help_text="0=Monday, 6=Sunday")
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.driver.name} – {self.frequency} from {self.effective_from}"