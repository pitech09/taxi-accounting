from django.db import models

class SystemSettings(models.Model):
    debt_cap = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    repayment_percentage = models.IntegerField(default=100)
    minimum_driver_take = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    company_name = models.CharField(max_length=200, default='My Transport Fleet')
    company_phone = models.CharField(max_length=20, blank=True)
    company_email = models.EmailField(blank=True)
    company_address = models.TextField(blank=True)
    company_logo = models.ImageField(upload_to='company/', null=True, blank=True)
    days_in_month_for_salary = models.IntegerField(default=30)
    contract_settlement_day = models.IntegerField(default=1, help_text="Day of month when contract is settled")

    # Cash book settings
    default_bank_account = models.ForeignKey(
        'cashbook.BankAccount', on_delete=models.SET_NULL, null=True, blank=True
    )
    cash_alert_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    bank_alert_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)

    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name
    
    class Meta:
        verbose_name_plural = "System Settings"