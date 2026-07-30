from django.core.management.base import BaseCommand
from datetime import date, timedelta
from drivers.models import Driver
from settlements.models import DailySettlement
from contracts.models import MonthlyContractSummary
import calendar

class Command(BaseCommand):
    help = 'Settle all contracts at month end'
    
    def add_arguments(self, parser):
        parser.add_argument('--month', type=int, help='Month to settle')
        parser.add_argument('--year', type=int, help='Year to settle')
    
    def handle(self, *args, **options):
        today = date.today()
        month = options.get('month', today.month)
        year = options.get('year', today.year)
        
        month_start = date(year, month, 1)
        _, days_in_month = calendar.monthrange(year, month)
        month_end = date(year, month, days_in_month)
        
        contract_drivers = Driver.objects.filter(vehicle__operating_model='contract', is_active=True)
        
        settled_count = 0
        for driver in contract_drivers:
            # Check if already settled
            if MonthlyContractSummary.objects.filter(driver=driver, year=year, month=month).exists():
                self.stdout.write(f"Skipping {driver.name} - already settled for {month}/{year}")
                continue
            
            settlements = DailySettlement.objects.filter(
                driver=driver,
                date__gte=month_start,
                date__lte=month_end,
                operating_model='contract'
            )
            
            if not settlements.exists():
                self.stdout.write(f"No settlements found for {driver.name}")
                continue
            
            monthly_gross = sum(s.total_income for s in settlements)
            total_expenses = sum(s.total_expenses for s in settlements)
            gross_profit = monthly_gross - total_expenses
            target = driver.effective_contract_target
            is_success = monthly_gross >= target
            
            if is_success:
                bonus_type = driver.vehicle.contract_success_bonus_type
                if bonus_type == 'fixed':
                    driver_pay = driver.effective_contract_success_bonus_fixed
                elif bonus_type == 'percentage':
                    driver_pay = (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
                else:
                    driver_pay = driver.effective_contract_success_bonus_fixed + \
                        (driver.effective_contract_success_bonus_percentage / 100) * monthly_gross
            else:
                driver_pay = (driver.effective_contract_failure_percentage / 100) * monthly_gross
            
            owner_pay = monthly_gross - driver_pay
            
            MonthlyContractSummary.objects.create(
                driver=driver,
                vehicle=driver.vehicle,
                year=year,
                month=month,
                target=target,
                total_gross=monthly_gross,
                total_expenses=total_expenses,
                gross_profit=gross_profit,
                is_success=is_success,
                bonus_type=driver.vehicle.contract_success_bonus_type if is_success else '',
                success_bonus_fixed=driver.effective_contract_success_bonus_fixed if is_success else 0,
                success_bonus_percentage=driver.effective_contract_success_bonus_percentage if is_success else 0,
                failure_percentage=driver.effective_contract_failure_percentage if not is_success else 0,
                driver_pay=driver_pay,
                owner_pay=owner_pay,
                days_worked=settlements.count(),
            )
            
            settled_count += 1
            self.stdout.write(self.style.SUCCESS(
                f"Settled {driver.name}: {'Success' if is_success else 'Failed'} - "
                f"Driver: M{driver_pay:.2f}, Owner: M{owner_pay:.2f}"
            ))
        
        self.stdout.write(self.style.SUCCESS(f"\nSettled {settled_count} contracts for {month}/{year}"))