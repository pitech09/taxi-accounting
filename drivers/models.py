import random
from django.db import models
from vehicles.models import Vehicle

class Driver(models.Model):
    # Personal info
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    id_number = models.CharField(max_length=50, blank=True)
    
    # Driver credentials
    license_type = models.CharField(max_length=10, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    
    # Current assignment
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='drivers')
    
    # Status
    is_active = models.BooleanField(default=True)
    hire_date = models.DateField(auto_now_add=True)
    termination_date = models.DateField(null=True, blank=True)
    
    # Portal login code (random 4 digits)
    driver_code = models.CharField(max_length=4, unique=True, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.driver_code:
            # Generate a unique random 4-digit code
            while True:
                code = str(random.randint(1000, 9999))
                if not Driver.objects.filter(driver_code=code).exists():
                    self.driver_code = code
                    break
        super().save(*args, **kwargs)
    
    # Model overrides (if different from vehicle defaults)
    daily_quota_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_salary_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentage_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Contract overrides
    contract_target_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    contract_success_bonus_fixed_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    contract_success_bonus_percentage_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    contract_failure_percentage_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Settlement frequency override
    settlement_frequency = models.CharField(max_length=10, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], blank=True, null=True, help_text="Override vehicle default")

    # Portal access
    portal_password = models.CharField(max_length=128, blank=True, null=True)
    is_portal_enabled = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
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
            return self.contract_success_bonus_fixed_override or self.vehicle.contract_success_bonus_fixed
        return 0
    
    @property
    def effective_contract_success_bonus_percentage(self):
        if self.vehicle and self.vehicle.operating_model == 'contract':
            return self.contract_success_bonus_percentage_override or self.vehicle.contract_success_bonus_percentage
        return 0
    
    @property
    def effective_contract_failure_percentage(self):
        if self.vehicle and self.vehicle.operating_model == 'contract':
            return self.contract_failure_percentage_override or self.vehicle.contract_failure_percentage
        return 0
    
    @property
    def debt_balance(self):
        from settlements.models import DailySettlement
        latest = DailySettlement.objects.filter(driver=self).order_by('-date').first()
        if latest and self.vehicle and self.vehicle.operating_model == 'quota':
            return latest.new_debt
        return 0
    
    @property
    def model_display(self):
        if self.vehicle:
            return self.vehicle.model_display
        return 'Not Assigned'