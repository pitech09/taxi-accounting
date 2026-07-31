"""
Driver model for the Taxi Accounting System.
Represents a taxi driver who may operate under any of the four operating models.
"""
from django.db import models
from django.urls import reverse
from django.contrib.auth.hashers import check_password, make_password
from vehicles.models import Vehicle


class Driver(models.Model):
    """A taxi driver assigned to a vehicle under a specific operating model."""

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    id_number = models.CharField(max_length=50, blank=True)

    license_type = models.CharField(max_length=50, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    license_expiry = models.DateField(null=True, blank=True)

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='drivers',
    )

    is_active = models.BooleanField(default=True)
    hire_date = models.DateField(auto_now_add=True)
    termination_date = models.DateField(null=True, blank=True)

    settlement_frequency = models.CharField(
        max_length=10,
        choices=[('daily', 'Daily'), ('weekly', 'Weekly')],
        blank=True,
        null=True,
        help_text='Override vehicle default',
    )

    # Per-driver overrides for operating-model parameters
    daily_quota_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_salary_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentage_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    contract_target_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    contract_success_bonus_fixed_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    contract_success_bonus_percentage_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    contract_failure_percentage_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Portal access
    driver_code = models.CharField(
        max_length=4,
        unique=True,
        blank=True,
        null=True,
        help_text='4-digit code for driver portal login'
    )
    portal_password = models.CharField(max_length=128, blank=True, null=True)
    is_portal_enabled = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)

    # Notes for owner/admin
    notes = models.TextField(blank=True, help_text='Internal notes about this driver')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.driver_code or 'no code'})"

    def get_absolute_url(self):
        """Link to driver detail in owner portal."""
        return reverse('owner_driver_detail', kwargs={'driver_id': self.id})

    # ------------------------------------------------------------------
    # Effective parameter helpers – fall back to vehicle defaults
    # ------------------------------------------------------------------
    @property
    def effective_quota(self):
        if self.vehicle and self.vehicle.operating_model == 'quota':
            return self.daily_quota_override or self.vehicle.daily_quota
        return 0

    @property
    def effective_salary(self):
        if self.vehicle and self.vehicle.operating_model == 'salary':
            return self.monthly_salary_override or self.vehicle.monthly_salary
        return 0

    @property
    def effective_percentage(self):
        if self.vehicle and self.vehicle.operating_model == 'percentage':
            return self.percentage_override or self.vehicle.driver_percentage
        return 0

    @property
    def effective_contract_target(self):
        if self.vehicle and self.vehicle.operating_model == 'contract':
            return self.contract_target_override or self.vehicle.contract_target
        return 0

    @property
    def effective_contract_success_bonus_fixed(self):
        if self.vehicle and self.vehicle.operating_model == 'contract':
            return (self.contract_success_bonus_fixed_override or
                    self.vehicle.contract_success_bonus_fixed)
        return 0

    @property
    def effective_contract_success_bonus_percentage(self):
        if self.vehicle and self.vehicle.operating_model == 'contract':
            return (self.contract_success_bonus_percentage_override or
                    self.vehicle.contract_success_bonus_percentage)
        return 0

    @property
    def effective_contract_failure_percentage(self):
        if self.vehicle and self.vehicle.operating_model == 'contract':
            return (self.contract_failure_percentage_override or
                    self.vehicle.contract_failure_percentage)
        return 0

    @property
    def model_display(self):
        """Return the operating model display name."""
        if self.vehicle:
            return self.vehicle.model_display
        return 'N/A'

    @property
    def effective_settlement_frequency(self):
        """Return the driver's settlement frequency, falling back to vehicle default."""
        if self.settlement_frequency:
            return self.settlement_frequency
        if self.vehicle:
            return self.vehicle.default_settlement_frequency
        return 'daily'

    @property
    def debt_balance(self):
        """Return the current debt balance for quota-model drivers."""
        latest = self.settlements.filter(status='approved').order_by('-date').first()
        if latest and self.vehicle and self.vehicle.operating_model == 'quota':
            return latest.new_debt
        return 0

    # ------------------------------------------------------------------
    # Portal authentication helpers
    # ------------------------------------------------------------------
    def check_portal_password(self, raw_password):
        """Check the raw password against the stored hash."""
        if not self.portal_password:
            return False
        return check_password(raw_password, self.portal_password)

    def set_portal_password(self, raw_password):
        """Set the portal password using Django's password hasher."""
        if raw_password:
            self.portal_password = make_password(raw_password)
        else:
            self.portal_password = None

    def save(self, *args, **kwargs):
        """Auto-generate a 4-digit driver code if not provided."""
        if not self.driver_code:
            import random
            for _ in range(10):
                code = f"{random.randint(1000, 9999)}"
                if not Driver.objects.filter(driver_code=code).exists():
                    self.driver_code = code
                    break
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['vehicle', 'is_active']),
            models.Index(fields=['driver_code']),
        ]