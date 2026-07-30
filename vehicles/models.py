from django.db import models

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('sedan', 'Sedan (4-seater)'),
        ('minivan', 'Minivan (6-8 seater)'),
        ('minibus', 'Minibus (14-seater)'),
        ('bus', 'Bus (30-50 seater)'),
    ]
    
    OPERATING_MODELS = [
        ('quota', 'Quota System'),
        ('salary', 'Monthly Salary'),
        ('percentage', 'Percentage System'),
        ('contract', 'Contract System'),
    ]
    
    name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    seats = models.PositiveIntegerField()
    plate = models.CharField(max_length=20, unique=True)
    
    # Operating model
    operating_model = models.CharField(max_length=20, choices=OPERATING_MODELS, default='quota')
    
    # Quota system fields
    daily_quota = models.DecimalField(max_digits=10, decimal_places=2, default=250.00,
                                       help_text="Only used for quota model")
    
    # Salary system fields
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2, default=3000.00,
                                          help_text="Only used for salary model")
    
    # Percentage system fields
    driver_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=30.00,
                                             help_text="Driver's percentage of gross income (e.g., 30%)")
    
    # Contract system fields
    contract_target = models.DecimalField(max_digits=10, decimal_places=2, default=15000.00,
                                           help_text="Monthly target gross income for contract model")
    contract_success_bonus_type = models.CharField(max_length=20, choices=[
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Gross'),
        ('hybrid', 'Hybrid (Fixed + Percentage)'),
    ], default='fixed', help_text="Only used for contract model")
    contract_success_bonus_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00,
                                                        help_text="Fixed bonus amount if target achieved")
    contract_success_bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00,
                                                             help_text="Percentage bonus if target achieved (e.g., 10%)")
    contract_failure_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=20.00,
                                                       help_text="Percentage of gross income driver keeps if target is NOT achieved")
    
    # Fixed monthly costs
    insurance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    permit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loan_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Settlement frequency
    default_settlement_frequency = models.CharField(max_length=10, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], default='daily')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_vehicle_type_display()})"
    
    @property
    def monthly_fixed_costs(self):
        return self.insurance + (self.permit_cost / 12) + self.loan_payment
    
    @property
    def model_display(self):
        return dict(self.OPERATING_MODELS)[self.operating_model]