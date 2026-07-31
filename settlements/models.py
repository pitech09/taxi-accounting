"""
Settlement models for the Taxi Accounting System.

DailySettlement captures a driver's income and expenses for a single day
(or a week for weekly settlements).  The save() method performs all
operating-model calculations and, when a settlement is approved,
automatically creates a CashTransaction that adds the owner's collection
to Cash in Hand.
"""
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone
from vehicles.models import Vehicle
from drivers.models import Driver


def _round2(value):
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    if value is None:
        return Decimal('0.00')
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _to_decimal(value):
    """Safely convert a value (str, int, float, Decimal, or None) to Decimal."""
    if value is None:
        return Decimal('0.00')
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class DailySettlement(models.Model):
    """A single settlement entry (daily or weekly) for a driver."""

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

    DEBT_STATUS_CHOICES = [
        ('none', 'No Debt'),
        ('accumulated', 'Debt Accumulated'),
        ('repaid', 'Debt Repaid'),
        ('partial', 'Partial Repayment'),
        ('overdue', 'Debt Cap Exceeded'),   # <-- NEW
    ]

    # Core references
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='settlements')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='settlements')
    operating_model = models.CharField(
        max_length=20,
        choices=Vehicle.OPERATING_MODELS,
        editable=False,
    )

    # Period information
    date = models.DateField(help_text='Primary date for this settlement')
    settlement_period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='daily')
    week_start = models.DateField(null=True, blank=True)
    week_end = models.DateField(null=True, blank=True)

    # Income
    cash_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mobile_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    card_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Expenses
    fuel_expense = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maintenance_expense = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    toll_expense = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_expense = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_expense_desc = models.CharField(max_length=200, blank=True)

    # Notes & workflow
    driver_notes = models.TextField(blank=True)
    owner_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_settlements',
    )

    # Auto-calculated fields (all editable=False)
    total_income = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    total_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    gross_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    # Quota model fields
    daily_quota = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    surplus_shortfall = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    debt_repaid = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    new_debt = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    quota_paid_to_owner = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    # Salary model fields
    daily_salary_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    monthly_salary_accumulated = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    # Percentage model fields
    driver_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    driver_percentage_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    owner_percentage_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    # Contract model fields
    contract_target = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    contract_monthly_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    contract_remaining_target = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    contract_driver_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    contract_driver_failure_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    contract_is_success = models.BooleanField(default=False, editable=False)
    contract_bonus_type = models.CharField(max_length=20, blank=True, editable=False)
    contract_success_bonus_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    contract_success_bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    contract_failure_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    contract_driver_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    contract_owner_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    # Final payouts
    driver_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    total_owner_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    # Debt tracking
    debt_status = models.CharField(max_length=20, choices=DEBT_STATUS_CHOICES, default='none', editable=False)

    # Cash book integration
    cash_added_to_hand = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    cash_transaction_created = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['driver', 'date']),
            models.Index(fields=['status', 'date']),
        ]

    def __str__(self):
        return f"{self.driver.name} - {self.date} ({self.get_status_display()})"

    def clean(self):
        """
        Prevent changing the status of an approved settlement.
        Once approved, a settlement is final and cannot be edited.
        """
        if self.pk:
            original = DailySettlement.objects.get(pk=self.pk)
            if original.status == 'approved' and self.status != original.status:
                raise ValidationError(
                    'Cannot change status of an approved settlement. '
                    'Create a new settlement instead.'
                )

    # ------------------------------------------------------------------
    # Calculation helpers
    # ------------------------------------------------------------------
    def _clear_calculations(self):
        """Reset all auto-calculated fields to zero."""
        self.total_income = Decimal('0.00')
        self.total_expenses = Decimal('0.00')
        self.gross_profit = Decimal('0.00')
        self.daily_quota = Decimal('0.00')
        self.surplus_shortfall = Decimal('0.00')
        self.debt_repaid = Decimal('0.00')
        self.new_debt = Decimal('0.00')
        self.quota_paid_to_owner = Decimal('0.00')
        self.daily_salary_earned = Decimal('0.00')
        self.monthly_salary_accumulated = Decimal('0.00')
        self.driver_percentage = Decimal('0.00')
        self.driver_percentage_amount = Decimal('0.00')
        self.owner_percentage_amount = Decimal('0.00')
        self.contract_target = Decimal('0.00')
        self.contract_monthly_gross = Decimal('0.00')
        self.contract_remaining_target = Decimal('0.00')
        self.contract_driver_bonus = Decimal('0.00')
        self.contract_driver_failure_amount = Decimal('0.00')
        self.contract_is_success = False
        self.contract_bonus_type = ''
        self.contract_success_bonus_fixed = Decimal('0.00')
        self.contract_success_bonus_percentage = Decimal('0.00')
        self.contract_failure_percentage = Decimal('0.00')
        self.contract_driver_pay = Decimal('0.00')
        self.contract_owner_pay = Decimal('0.00')
        self.driver_pay = Decimal('0.00')
        self.total_owner_collected = Decimal('0.00')
        self.debt_status = 'none'
        self.cash_added_to_hand = Decimal('0.00')

    def _calculate_totals(self):
        """Calculate total income and total expenses.

        Values are explicitly converted to Decimal to handle cases where
        they may be strings (e.g. when assigned directly from request.POST
        in the owner portal views).  Without this conversion, the ``+``
        operator would perform string concatenation instead of numeric
        addition, producing wildly incorrect totals.
        """
        cash = _to_decimal(self.cash_collected)
        mobile = _to_decimal(self.mobile_collected)
        card = _to_decimal(self.card_collected)
        fuel = _to_decimal(self.fuel_expense)
        maintenance = _to_decimal(self.maintenance_expense)
        toll = _to_decimal(self.toll_expense)
        other = _to_decimal(self.other_expense)

        self.total_income = _round2(cash + mobile + card)
        self.total_expenses = _round2(fuel + maintenance + toll + other)
        self.gross_profit = _round2(self.total_income - self.total_expenses)

    def _get_previous_debt(self):
        """Return the debt carried over from the latest approved settlement.

        Debt is tied to the driver, not the vehicle, so that if a driver
        changes vehicles the debt persists.  Only approved settlements
        are considered – drafts, submitted, and rejected are excluded.
        """
        latest_approved = self.driver.settlements.filter(
            status='approved', operating_model='quota'
        ).exclude(pk=self.pk).order_by('-date').first()
        if latest_approved:
            return _to_decimal(latest_approved.new_debt)
        return Decimal('0.00')

    def _calculate_quota(self):
        """Quota model: driver pays daily fixed quota; keeps surplus; debt on shortfall.

        Business rules:
        - gross_profit = total_income - total_expenses
        - If gross_profit >= quota:
            surplus = gross_profit - quota
            debt_repaid = min(previous_debt, surplus)
            new_debt = previous_debt - debt_repaid
            driver_pay = surplus - debt_repaid
            quota_paid_to_owner = quota
            total_owner_collected = quota + debt_repaid
        - If gross_profit < quota:
            new_debt = previous_debt + (quota - gross_profit)
            driver_pay = 0
            quota_paid_to_owner = max(0, gross_profit)   # <-- FIXED: clamp to 0
            total_owner_collected = quota_paid_to_owner
        """
        from accounts.models import SystemSettings
        settings = SystemSettings.get_settings()

        self.daily_quota = _round2(self.driver.effective_quota)
        previous_debt = self._get_previous_debt()

        daily_gross = self.gross_profit

        if daily_gross >= self.daily_quota:
            # Surplus case: quota is met, surplus is available
            surplus = _round2(daily_gross - self.daily_quota)
            self.surplus_shortfall = surplus

            # Repay debt first from surplus
            self.debt_repaid = _round2(min(surplus, previous_debt))
            self.new_debt = _round2(max(Decimal('0.00'), previous_debt - self.debt_repaid))

            # Driver only gets paid after debt is repaid
            self.driver_pay = _round2(surplus - self.debt_repaid)
            self.quota_paid_to_owner = _round2(self.daily_quota)

            # Debt status
            if previous_debt > 0 and self.new_debt == 0:
                self.debt_status = 'repaid'
            elif self.new_debt > 0:
                self.debt_status = 'partial'
            else:
                self.debt_status = 'none'
        else:
            # Shortfall case: gross profit below quota
            shortfall = _round2(self.daily_quota - daily_gross)
            self.surplus_shortfall = _round2(Decimal('0.00') - shortfall)  # negative value

            self.debt_repaid = Decimal('0.00')
            self.new_debt = _round2(previous_debt + shortfall)
            self.driver_pay = Decimal('0.00')
            # Owner gets nothing if gross profit is negative
            self.quota_paid_to_owner = _round2(max(Decimal('0.00'), daily_gross))
            self.debt_status = 'accumulated'

        # Cap debt at settings.debt_cap
        if self.new_debt > settings.debt_cap:
            self.new_debt = _round2(settings.debt_cap)
            self.debt_status = 'overdue'   # <-- NEW: flag debt cap exceeded

        # total_owner_collected = quota_paid_to_owner + debt_repaid
        self.total_owner_collected = _round2(self.quota_paid_to_owner + self.debt_repaid)
        self.cash_added_to_hand = self.total_owner_collected

    def _calculate_salary(self):
        """Salary model: driver receives fixed monthly salary; owner keeps all gross profit after salary.

        Business rules:
        - daily_salary = monthly_salary / days_in_month
        - driver_pay = daily_salary
        - total_owner_collected = gross_profit - driver_pay
        """
        from accounts.models import SystemSettings
        settings = SystemSettings.get_settings()

        monthly_salary = _round2(self.driver.effective_salary)
        daily_rate = _round2(monthly_salary / settings.days_in_month_for_salary)

        self.daily_salary_earned = daily_rate
        self.monthly_salary_accumulated = _round2(
            self.driver.settlements.filter(
                status='approved', operating_model='salary',
                date__year=self.date.year, date__month=self.date.month
            ).exclude(pk=self.pk).count() * daily_rate + daily_rate
        )

        # Driver gets daily salary; owner gets gross profit minus salary
        self.driver_pay = daily_rate
        self.total_owner_collected = _round2(self.gross_profit - daily_rate)
        self.cash_added_to_hand = self.total_owner_collected

    def _calculate_percentage(self):
        """Percentage model: driver receives fixed percentage of total income.

        Business rules:
        - driver_pay = (driver_percentage / 100) * total_income
        - total_owner_collected = total_income - driver_pay
        - Expenses are NOT deducted from the driver's share.
        - Owner bears all expenses.
        """
        percentage = _round2(self.driver.effective_percentage)
        self.driver_percentage = percentage
        self.driver_percentage_amount = _round2((percentage / 100) * self.total_income)
        self.owner_percentage_amount = _round2(self.total_income - self.driver_percentage_amount)
        self.driver_pay = self.driver_percentage_amount
        self.total_owner_collected = _round2(self.owner_percentage_amount)
        self.cash_added_to_hand = self.total_owner_collected

    def _calculate_contract(self):
        """Contract model: target-based with success bonus or failure percentage.

        Business rules:
        - target = monthly target
        - monthly_gross = sum of total_income for all approved settlements in the month
        - If monthly_gross >= target (success):
            - Fixed: driver_bonus = success_bonus_fixed
            - Percentage: driver_bonus = (success_bonus_percentage / 100) * monthly_gross
            - Hybrid: driver_bonus = fixed + (percentage / 100) * monthly_gross
            - driver_pay = driver_bonus / days_worked (daily estimate)
            - total_owner_collected = total_income - driver_pay
        - If monthly_gross < target (failure):
            - driver_pay = (failure_percentage / 100) * total_income (daily estimate)
            - total_owner_collected = total_income - driver_pay
        """
        from accounts.models import SystemSettings
        settings = SystemSettings.get_settings()

        target = _round2(self.driver.effective_contract_target)
        self.contract_target = target

        # Calculate monthly gross so far (including this settlement)
        month_start = self.date.replace(day=1)
        monthly_settlements = self.driver.settlements.filter(
            status='approved', operating_model='contract',
            date__year=self.date.year, date__month=self.date.month
        ).exclude(pk=self.pk)

        monthly_gross = _round2(
            sum(s.total_income for s in monthly_settlements) + self.total_income
        )
        self.contract_monthly_gross = monthly_gross
        self.contract_remaining_target = _round2(max(Decimal('0.00'), target - monthly_gross))

        # Determine success/failure
        is_success = monthly_gross >= target
        self.contract_is_success = is_success

        bonus_type = self.driver.vehicle.contract_success_bonus_type
        self.contract_bonus_type = bonus_type
        self.contract_success_bonus_fixed = _round2(self.driver.effective_contract_success_bonus_fixed)
        self.contract_success_bonus_percentage = _round2(self.driver.effective_contract_success_bonus_percentage)
        self.contract_failure_percentage = _round2(self.driver.effective_contract_failure_percentage)

        # Calculate days worked in the month (approved contract settlements)
        days_worked = monthly_settlements.count() + 1  # +1 for current settlement

        if is_success:
            if bonus_type == 'fixed':
                self.contract_driver_bonus = self.contract_success_bonus_fixed
            elif bonus_type == 'percentage':
                self.contract_driver_bonus = _round2(
                    (self.contract_success_bonus_percentage / 100) * monthly_gross
                )
            else:  # hybrid
                self.contract_driver_bonus = _round2(
                    self.contract_success_bonus_fixed +
                    (self.contract_success_bonus_percentage / 100) * monthly_gross
                )
            self.contract_driver_failure_amount = Decimal('0.00')
            # Daily estimate: driver_bonus / days_worked
            self.contract_driver_pay = _round2(self.contract_driver_bonus / days_worked)
        else:
            self.contract_driver_bonus = Decimal('0.00')
            # Failure: driver_pay = (failure_percentage / 100) * total_income (daily)
            self.contract_driver_failure_amount = _round2(
                (self.contract_failure_percentage / 100) * self.total_income
            )
            self.contract_driver_pay = self.contract_driver_failure_amount

        self.contract_owner_pay = _round2(self.total_income - self.contract_driver_pay)
        self.driver_pay = self.contract_driver_pay
        self.total_owner_collected = _round2(self.total_income - self.driver_pay)
        self.cash_added_to_hand = self.total_owner_collected

    def _run_calculations(self):
        """Run the appropriate calculation based on operating model."""
        self._calculate_totals()
        model = self.vehicle.operating_model if self.vehicle else 'quota'
        if model == 'quota':
            self._calculate_quota()
        elif model == 'salary':
            self._calculate_salary()
        elif model == 'percentage':
            self._calculate_percentage()
        elif model == 'contract':
            self._calculate_contract()

    # ------------------------------------------------------------------
    # Cash transaction creation
    # ------------------------------------------------------------------
    def _create_cash_transaction(self):
        """Create a CashTransaction for the owner's collection."""
        from cashbook.models import CashTransaction
        CashTransaction.objects.create(
            transaction_type='settlement_collection',
            category='settlement_collection',
            amount=self.total_owner_collected,
            date=self.date,
            settlement=self,
            notes=f"Collection from {self.driver.name} - {self.operating_model} - {self.vehicle.name}",
            created_by=self.approved_by,
        )

    # ------------------------------------------------------------------
    # Save override
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):
        """
        On save:
        - Set operating_model from vehicle.
        - If status == 'approved':
          run calculations, create/update CashTransaction.
        - If status != 'approved', clear all calculation fields.
        """
        # Run full validation
        self.full_clean()

        # Set operating model from vehicle
        if self.vehicle:
            self.operating_model = self.vehicle.operating_model

        # Set submitted_at when transitioning to submitted
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()

        # Set approved_at when transitioning to approved
        if self.status == 'approved' and not self.approved_at:
            self.approved_at = timezone.now()

        if self.status == 'approved':
            # Run calculations
            self._run_calculations()
            self.cash_added_to_hand = self.total_owner_collected

            # Save the settlement first so it has a primary key
            super().save(*args, **kwargs)

            # Create or update cash transaction
            if not self.cash_transaction_created and self.total_owner_collected > 0:
                self._create_cash_transaction()
                self.cash_transaction_created = True
                # Persist the flag
                super().save(update_fields=['cash_transaction_created'])
            else:
                # Update existing cash transaction if amount changed
                from cashbook.models import CashTransaction
                try:
                    ct = CashTransaction.objects.get(settlement=self)
                    if ct.amount != self.total_owner_collected:
                        ct.amount = self.total_owner_collected
                        ct.save()
                except CashTransaction.DoesNotExist:
                    pass
        else:
            # Clear calculations for non-approved settlements.
            # (Note: we prevent changing status away from 'approved' via clean())
            self._clear_calculations()
            super().save(*args, **kwargs)