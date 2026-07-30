from django.db import models
from vehicles.models import Vehicle
from drivers.models import Driver

class MonthlyContractSummary(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    
    target = models.DecimalField(max_digits=12, decimal_places=2)
    total_gross = models.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    is_success = models.BooleanField(default=False)
    bonus_type = models.CharField(max_length=20, blank=True)
    success_bonus_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    success_bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    failure_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    driver_pay = models.DecimalField(max_digits=12, decimal_places=2)
    owner_pay = models.DecimalField(max_digits=12, decimal_places=2)
    
    days_worked = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['driver', 'year', 'month']
    
    def __str__(self):
        return f"{self.driver.name} - {self.month}/{self.year}"