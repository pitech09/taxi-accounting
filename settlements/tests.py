"""
Unit tests for DailySettlement calculation logic.

Tests cover all four operating models (quota, salary, percentage, contract)
and verify that calculations match the business rules exactly.

Test cases:
  1. Quota – Good Day, No Debt
  2. Quota – Good Day, With Debt
  3. Quota – Bad Day
  4. Salary
  5. Percentage
  6. Contract – Success
  7. Contract – Failure
  Plus additional edge-case tests for debt tracking, cash transactions,
  and non-approved settlement handling.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import SystemSettings
from cashbook.models import CashTransaction
from drivers.models import Driver
from settlements.models import DailySettlement
from vehicles.models import Vehicle

User = get_user_model()


class SettlementTestBase(TestCase):
    """Shared setup: create a user, vehicle, driver, and system settings."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='owner', password='pass123')
        cls.settings = SystemSettings.get_settings()
        cls.settings.days_in_month_for_salary = 30
        cls.settings.debt_cap = Decimal('500.00')
        cls.settings.save()

    def _make_vehicle(self, operating_model='quota', **kwargs):
        """Create a vehicle with the given operating model and parameters."""
        defaults = {
            'name': 'Test Vehicle',
            'vehicle_type': 'sedan',
            'seats': 4,
            'plate': f'ABC-{operating_model[:3]}-{self._seq()}',
            'operating_model': operating_model,
            'daily_quota': Decimal('250.00'),
            'monthly_salary': Decimal('3000.00'),
            'driver_percentage': Decimal('30.00'),
            'contract_target': Decimal('15000.00'),
            'contract_success_bonus_type': 'fixed',
            'contract_success_bonus_fixed': Decimal('2000.00'),
            'contract_success_bonus_percentage': Decimal('10.00'),
            'contract_failure_percentage': Decimal('20.00'),
        }
        defaults.update(kwargs)
        return Vehicle.objects.create(**defaults)

    def _make_driver(self, vehicle, **kwargs):
        """Create a driver assigned to the given vehicle."""
        defaults = {
            'name': 'Test Driver',
            'phone': f'0700{self._seq()}',
            'vehicle': vehicle,
        }
        defaults.update(kwargs)
        return Driver.objects.create(**defaults)

    def _make_settlement(self, driver, vehicle, **kwargs):
        """Create and save a DailySettlement with the given parameters."""
        defaults = {
            'driver': driver,
            'vehicle': vehicle,
            'date': date(2026, 7, 15),
            'cash_collected': Decimal('0.00'),
            'mobile_collected': Decimal('0.00'),
            'card_collected': Decimal('0.00'),
            'fuel_expense': Decimal('0.00'),
            'maintenance_expense': Decimal('0.00'),
            'toll_expense': Decimal('0.00'),
            'other_expense': Decimal('0.00'),
            'status': 'approved',
            'approved_by': self.user,
        }
        defaults.update(kwargs)
        return DailySettlement.objects.create(**defaults)

    _counter = 0

    def _seq(self):
        self.__class__._counter += 1
        return str(self.__class__._counter).zfill(4)


class QuotaModelTests(SettlementTestBase):
    """Tests for the Quota System operating model."""

    def test_quota_good_day_no_debt(self):
        """Test Case 1: Quota – Good Day, No Debt.

        Quota = 250, gross_profit = 1890, previous_debt = 0
        Expected:
          surplus_shortfall = 1640
          debt_repaid = 0
          new_debt = 0
          driver_pay = 1640
          quota_paid_to_owner = 250
          total_owner_collected = 250
        """
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        # total_income = 2000, expenses = 110, gross_profit = 1890
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('2000.00'),
            fuel_expense=Decimal('110.00'),
        )
        self.assertEqual(settlement.gross_profit, Decimal('1890.00'))
        self.assertEqual(settlement.surplus_shortfall, Decimal('1640.00'))
        self.assertEqual(settlement.debt_repaid, Decimal('0.00'))
        self.assertEqual(settlement.new_debt, Decimal('0.00'))
        self.assertEqual(settlement.driver_pay, Decimal('1640.00'))
        self.assertEqual(settlement.quota_paid_to_owner, Decimal('250.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('250.00'))
        self.assertEqual(settlement.debt_status, 'none')

    def test_quota_good_day_with_debt(self):
        """Test Case 2: Quota – Good Day, With Debt.

        Quota = 250, gross_profit = 300, previous_debt = 50
        Expected:
          surplus_shortfall = 50
          debt_repaid = 50
          new_debt = 0
          driver_pay = 0
          quota_paid_to_owner = 250
          total_owner_collected = 300
        """
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        # First settlement creates debt of 50 (gross_profit=200, quota=250, shortfall=50)
        self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 10),
            cash_collected=Decimal('200.00'),
        )
        # Second settlement: gross_profit=300, quota=250, surplus=50, debt_repaid=50
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('300.00'),
        )
        self.assertEqual(settlement.gross_profit, Decimal('300.00'))
        self.assertEqual(settlement.surplus_shortfall, Decimal('50.00'))
        self.assertEqual(settlement.debt_repaid, Decimal('50.00'))
        self.assertEqual(settlement.new_debt, Decimal('0.00'))
        self.assertEqual(settlement.driver_pay, Decimal('0.00'))
        self.assertEqual(settlement.quota_paid_to_owner, Decimal('250.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('300.00'))
        self.assertEqual(settlement.debt_status, 'repaid')

    def test_quota_bad_day(self):
        """Test Case 3: Quota – Bad Day.

        Quota = 250, gross_profit = 180, previous_debt = 50
        Expected:
          surplus_shortfall = -70
          debt_repaid = 0
          new_debt = 120
          driver_pay = 0
          quota_paid_to_owner = 180
          total_owner_collected = 180
        """
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        # First settlement creates debt of 50
        self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 10),
            cash_collected=Decimal('200.00'),
        )
        # Second settlement: gross_profit=180, quota=250, shortfall=70, new_debt=120
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('180.00'),
        )
        self.assertEqual(settlement.gross_profit, Decimal('180.00'))
        self.assertEqual(settlement.surplus_shortfall, Decimal('-70.00'))
        self.assertEqual(settlement.debt_repaid, Decimal('0.00'))
        self.assertEqual(settlement.new_debt, Decimal('120.00'))
        self.assertEqual(settlement.driver_pay, Decimal('0.00'))
        self.assertEqual(settlement.quota_paid_to_owner, Decimal('180.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('180.00'))
        self.assertEqual(settlement.debt_status, 'accumulated')

    def test_quota_debt_persists_across_vehicles(self):
        """Debt is tied to the driver, not the vehicle.

        If a driver changes vehicles, the debt should persist.
        """
        vehicle1 = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'),
                                      plate='ABC-001')
        vehicle2 = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'),
                                      plate='ABC-002')
        driver = self._make_driver(vehicle1)
        # First settlement on vehicle1 creates debt of 50
        self._make_settlement(
            driver, vehicle1,
            date=date(2026, 7, 10),
            cash_collected=Decimal('200.00'),
        )
        # Change driver's vehicle
        driver.vehicle = vehicle2
        driver.save()
        # Second settlement on vehicle2 should still see previous debt
        settlement = self._make_settlement(
            driver, vehicle2,
            date=date(2026, 7, 15),
            cash_collected=Decimal('300.00'),
        )
        self.assertEqual(settlement.debt_repaid, Decimal('50.00'))
        self.assertEqual(settlement.new_debt, Decimal('0.00'))
        self.assertEqual(settlement.driver_pay, Decimal('0.00'))

    def test_quota_partial_debt_repayment(self):
        """Test partial debt repayment when surplus is less than debt."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        # First settlement: gross_profit=200, quota=250, shortfall=50, debt=50
        self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 10),
            cash_collected=Decimal('200.00'),
        )
        # Second settlement: gross_profit=280, quota=250, surplus=30, debt_repaid=30, new_debt=20
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('280.00'),
        )
        self.assertEqual(settlement.surplus_shortfall, Decimal('30.00'))
        self.assertEqual(settlement.debt_repaid, Decimal('30.00'))
        self.assertEqual(settlement.new_debt, Decimal('20.00'))
        self.assertEqual(settlement.driver_pay, Decimal('0.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('280.00'))
        self.assertEqual(settlement.debt_status, 'partial')

    def test_quota_debt_cap(self):
        """Test that debt is capped at settings.debt_cap."""
        self.settings.debt_cap = Decimal('100.00')
        self.settings.save()
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        # gross_profit=0, quota=250, shortfall=250, but debt capped at 100
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('0.00'),
        )
        self.assertEqual(settlement.new_debt, Decimal('100.00'))


class SalaryModelTests(SettlementTestBase):
    """Tests for the Monthly Salary System operating model."""

    def test_salary_basic(self):
        """Test Case 4: Salary.

        monthly_salary = 3000, gross_profit = 1890, days_in_month = 30
        Expected:
          daily_salary_earned = 100
          driver_pay = 100
          total_owner_collected = 1790
        """
        vehicle = self._make_vehicle(operating_model='salary', monthly_salary=Decimal('3000.00'))
        driver = self._make_driver(vehicle)
        # total_income = 2000, expenses = 110, gross_profit = 1890
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('2000.00'),
            fuel_expense=Decimal('110.00'),
        )
        self.assertEqual(settlement.gross_profit, Decimal('1890.00'))
        self.assertEqual(settlement.daily_salary_earned, Decimal('100.00'))
        self.assertEqual(settlement.driver_pay, Decimal('100.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('1790.00'))

    def test_salary_monthly_accumulated(self):
        """Test that monthly_salary_accumulated tracks the running total for the month."""
        vehicle = self._make_vehicle(operating_model='salary', monthly_salary=Decimal('3000.00'))
        driver = self._make_driver(vehicle)
        # First settlement
        s1 = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 10),
            cash_collected=Decimal('2000.00'),
        )
        self.assertEqual(s1.monthly_salary_accumulated, Decimal('100.00'))
        # Second settlement
        s2 = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('2000.00'),
        )
        self.assertEqual(s2.monthly_salary_accumulated, Decimal('200.00'))

    def test_salary_loss_for_owner(self):
        """If gross_profit < driver_pay, owner makes a loss."""
        vehicle = self._make_vehicle(operating_model='salary', monthly_salary=Decimal('3000.00'))
        driver = self._make_driver(vehicle)
        # gross_profit = 50, daily_salary = 100, owner collects -50
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('50.00'),
        )
        self.assertEqual(settlement.gross_profit, Decimal('50.00'))
        self.assertEqual(settlement.driver_pay, Decimal('100.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('-50.00'))


class PercentageModelTests(SettlementTestBase):
    """Tests for the Percentage System operating model."""

    def test_percentage_basic(self):
        """Test Case 5: Percentage.

        driver_percentage = 30, total_income = 2800, expenses = 910
        Expected:
          total_income = 2800
          driver_pay = 840
          total_owner_collected = 1960
        """
        vehicle = self._make_vehicle(operating_model='percentage', driver_percentage=Decimal('30.00'))
        driver = self._make_driver(vehicle)
        # total_income = 2800, expenses = 910, gross_profit = 1890
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('2800.00'),
            fuel_expense=Decimal('910.00'),
        )
        self.assertEqual(settlement.total_income, Decimal('2800.00'))
        self.assertEqual(settlement.gross_profit, Decimal('1890.00'))
        self.assertEqual(settlement.driver_percentage, Decimal('30.00'))
        self.assertEqual(settlement.driver_percentage_amount, Decimal('840.00'))
        self.assertEqual(settlement.driver_pay, Decimal('840.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('1960.00'))

    def test_percentage_uses_total_income_not_gross_profit(self):
        """Percentage is calculated on total_income, not gross_profit."""
        vehicle = self._make_vehicle(operating_model='percentage', driver_percentage=Decimal('30.00'))
        driver = self._make_driver(vehicle)
        # total_income = 1000, expenses = 500, gross_profit = 500
        # driver_pay should be 30% of 1000 = 300, not 30% of 500 = 150
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('1000.00'),
            fuel_expense=Decimal('500.00'),
        )
        self.assertEqual(settlement.driver_pay, Decimal('300.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('700.00'))


class ContractModelTests(SettlementTestBase):
    """Tests for the Contract (Target) System operating model."""

    def test_contract_success_fixed_bonus(self):
        """Test Case 6: Contract – Success.

        target = 15000, monthly_gross = 16000, bonus_type = 'fixed',
        success_bonus_fixed = 2000, days_worked = 20
        Expected:
          contract_is_success = True
          driver_bonus = 2000
          driver_pay = 100 (daily)
          total_owner_collected = 2800 - 100 = 2700 (daily)
        """
        vehicle = self._make_vehicle(
            operating_model='contract',
            contract_target=Decimal('15000.00'),
            contract_success_bonus_type='fixed',
            contract_success_bonus_fixed=Decimal('2000.00'),
        )
        driver = self._make_driver(vehicle)
        # Create 19 prior approved settlements with total_income=800 each
        # 19 * 800 = 15200, plus this one 800 = 16000 >= 15000
        for i in range(19):
            self._make_settlement(
                driver, vehicle,
                date=date(2026, 7, 1 + i),
                cash_collected=Decimal('800.00'),
            )
        # 20th settlement: total_income=800, monthly_gross=16000
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 20),
            cash_collected=Decimal('800.00'),
        )
        self.assertTrue(settlement.contract_is_success)
        self.assertEqual(settlement.contract_monthly_gross, Decimal('16000.00'))
        self.assertEqual(settlement.contract_driver_bonus, Decimal('2000.00'))
        self.assertEqual(settlement.contract_driver_pay, Decimal('100.00'))
        self.assertEqual(settlement.driver_pay, Decimal('100.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('700.00'))

    def test_contract_success_percentage_bonus(self):
        """Test contract success with percentage bonus type."""
        vehicle = self._make_vehicle(
            operating_model='contract',
            contract_target=Decimal('15000.00'),
            contract_success_bonus_type='percentage',
            contract_success_bonus_percentage=Decimal('10.00'),
        )
        driver = self._make_driver(vehicle)
        # 19 prior settlements * 800 = 15200, + 800 = 16000
        for i in range(19):
            self._make_settlement(
                driver, vehicle,
                date=date(2026, 7, 1 + i),
                cash_collected=Decimal('800.00'),
            )
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 20),
            cash_collected=Decimal('800.00'),
        )
        self.assertTrue(settlement.contract_is_success)
        # bonus = 10% of 16000 = 1600, daily = 1600/20 = 80
        self.assertEqual(settlement.contract_driver_bonus, Decimal('1600.00'))
        self.assertEqual(settlement.contract_driver_pay, Decimal('80.00'))
        self.assertEqual(settlement.driver_pay, Decimal('80.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('720.00'))

    def test_contract_success_hybrid_bonus(self):
        """Test contract success with hybrid bonus type."""
        vehicle = self._make_vehicle(
            operating_model='contract',
            contract_target=Decimal('15000.00'),
            contract_success_bonus_type='hybrid',
            contract_success_bonus_fixed=Decimal('1000.00'),
            contract_success_bonus_percentage=Decimal('5.00'),
        )
        driver = self._make_driver(vehicle)
        for i in range(19):
            self._make_settlement(
                driver, vehicle,
                date=date(2026, 7, 1 + i),
                cash_collected=Decimal('800.00'),
            )
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 20),
            cash_collected=Decimal('800.00'),
        )
        self.assertTrue(settlement.contract_is_success)
        # bonus = 1000 + 5% of 16000 = 1000 + 800 = 1800, daily = 1800/20 = 90
        self.assertEqual(settlement.contract_driver_bonus, Decimal('1800.00'))
        self.assertEqual(settlement.contract_driver_pay, Decimal('90.00'))
        self.assertEqual(settlement.driver_pay, Decimal('90.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('710.00'))

    def test_contract_failure(self):
        """Test Case 7: Contract – Failure.

        target = 15000, monthly_gross = 12000, failure_percentage = 20,
        total_income = 2800
        Expected:
          contract_is_success = False
          driver_pay = 560 (20% of daily income)
          total_owner_collected = 2800 - 560 = 2240
        """
        vehicle = self._make_vehicle(
            operating_model='contract',
            contract_target=Decimal('15000.00'),
            contract_failure_percentage=Decimal('20.00'),
        )
        driver = self._make_driver(vehicle)
        # 1 prior settlement with total_income=9200, + 2800 = 12000 < 15000
        self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 10),
            cash_collected=Decimal('9200.00'),
        )
        # 2nd settlement: total_income=2800, monthly_gross=12000
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 11),
            cash_collected=Decimal('2800.00'),
        )
        self.assertFalse(settlement.contract_is_success)
        self.assertEqual(settlement.contract_monthly_gross, Decimal('12000.00'))
        # driver_pay = 20% of total_income (2800) = 560
        self.assertEqual(settlement.contract_driver_failure_amount, Decimal('560.00'))
        self.assertEqual(settlement.contract_driver_pay, Decimal('560.00'))
        self.assertEqual(settlement.driver_pay, Decimal('560.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('2240.00'))


    def test_contract_remaining_target(self):
        """Test that contract_remaining_target is calculated correctly."""
        vehicle = self._make_vehicle(
            operating_model='contract',
            contract_target=Decimal('15000.00'),
        )
        driver = self._make_driver(vehicle)
        # 5 prior settlements * 1000 = 5000, + 1000 = 6000
        for i in range(5):
            self._make_settlement(
                driver, vehicle,
                date=date(2026, 7, 1 + i),
                cash_collected=Decimal('1000.00'),
            )
        settlement = self._make_settlement(
            driver, vehicle,
            date=date(2026, 7, 6),
            cash_collected=Decimal('1000.00'),
        )
        self.assertEqual(settlement.contract_remaining_target, Decimal('9000.00'))


class CashTransactionTests(SettlementTestBase):
    """Tests for cash transaction creation logic."""

    def test_cash_transaction_created_on_approval(self):
        """A CashTransaction is created when a settlement is approved."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('2000.00'),
            fuel_expense=Decimal('110.00'),
        )
        # total_owner_collected = 250 (quota) + 0 (debt_repaid) = 250
        ct = CashTransaction.objects.filter(settlement=settlement)
        self.assertEqual(ct.count(), 1)
        self.assertEqual(ct.first().transaction_type, 'settlement_collection')
        self.assertEqual(ct.first().category, 'settlement_collection')
        self.assertEqual(ct.first().amount, Decimal('250.00'))
        self.assertEqual(ct.first().date, settlement.date)
        self.assertEqual(ct.first().created_by, self.user)
        self.assertIn(driver.name, ct.first().notes)
        self.assertIn('quota', ct.first().notes)
        self.assertIn(vehicle.name, ct.first().notes)
        self.assertTrue(settlement.cash_transaction_created)

    def test_no_cash_transaction_for_draft(self):
        """No CashTransaction is created for draft settlements."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        settlement = DailySettlement(
            driver=driver,
            vehicle=vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('2000.00'),
            status='draft',
        )
        settlement.save()
        self.assertFalse(settlement.cash_transaction_created)
        self.assertEqual(CashTransaction.objects.filter(settlement=settlement).count(), 0)

    def test_no_cash_transaction_for_rejected(self):
        """No CashTransaction is created for rejected settlements."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        settlement = DailySettlement(
            driver=driver,
            vehicle=vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('2000.00'),
            status='rejected',
        )
        settlement.save()
        self.assertFalse(settlement.cash_transaction_created)
        self.assertEqual(CashTransaction.objects.filter(settlement=settlement).count(), 0)

    def test_no_duplicate_cash_transaction_on_reapprove(self):
        """Re-approving a settlement does not create a duplicate CashTransaction."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('2000.00'),
            fuel_expense=Decimal('110.00'),
        )
        # Should have exactly 1 cash transaction
        self.assertEqual(CashTransaction.objects.filter(settlement=settlement).count(), 1)
        # Re-save (simulating an edit to an approved settlement)
        settlement.cash_collected = Decimal('2100.00')
        settlement.save()
        # Still should have exactly 1 cash transaction (updated, not duplicated)
        self.assertEqual(CashTransaction.objects.filter(settlement=settlement).count(), 1)

    def test_cash_transaction_not_created_when_owner_collected_is_zero(self):
        """No CashTransaction when total_owner_collected is 0 or negative."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        # gross_profit = 0, quota = 250, shortfall = 250
        # total_owner_collected = gross_profit = 0
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('0.00'),
        )
        self.assertEqual(settlement.total_owner_collected, Decimal('0.00'))
        self.assertFalse(settlement.cash_transaction_created)
        self.assertEqual(CashTransaction.objects.filter(settlement=settlement).count(), 0)


class NonApprovedSettlementTests(SettlementTestBase):
    """Tests for non-approved settlement handling."""

    def test_draft_settlement_clears_calculations(self):
        """Draft settlements have all calculation fields cleared."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        settlement = DailySettlement(
            driver=driver,
            vehicle=vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('2000.00'),
            fuel_expense=Decimal('110.00'),
            status='draft',
        )
        settlement.save()
        self.assertEqual(settlement.total_income, Decimal('0.00'))
        self.assertEqual(settlement.gross_profit, Decimal('0.00'))
        self.assertEqual(settlement.driver_pay, Decimal('0.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('0.00'))
        self.assertEqual(settlement.debt_status, 'none')

    def test_rejected_settlement_clears_calculations(self):
        """Rejected settlements have all calculation fields cleared."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        settlement = DailySettlement(
            driver=driver,
            vehicle=vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('2000.00'),
            fuel_expense=Decimal('110.00'),
            status='rejected',
        )
        settlement.save()
        self.assertEqual(settlement.total_income, Decimal('0.00'))
        self.assertEqual(settlement.gross_profit, Decimal('0.00'))
        self.assertEqual(settlement.driver_pay, Decimal('0.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('0.00'))

    def test_operating_model_read_from_vehicle(self):
        """operating_model is read from the vehicle, not from a stored field."""
        vehicle = self._make_vehicle(operating_model='percentage', driver_percentage=Decimal('30.00'))
        driver = self._make_driver(vehicle)
        settlement = self._make_settlement(
            driver, vehicle,
            cash_collected=Decimal('1000.00'),
        )
        self.assertEqual(settlement.operating_model, 'percentage')

    def test_submitted_settlement_clears_calculations(self):
        """Submitted (but not yet approved) settlements have calculations cleared."""
        vehicle = self._make_vehicle(operating_model='quota', daily_quota=Decimal('250.00'))
        driver = self._make_driver(vehicle)
        settlement = DailySettlement(
            driver=driver,
            vehicle=vehicle,
            date=date(2026, 7, 15),
            cash_collected=Decimal('2000.00'),
            fuel_expense=Decimal('110.00'),
            status='submitted',
        )
        settlement.save()
        self.assertEqual(settlement.total_income, Decimal('0.00'))
        self.assertEqual(settlement.driver_pay, Decimal('0.00'))
        self.assertEqual(settlement.total_owner_collected, Decimal('0.00'))

