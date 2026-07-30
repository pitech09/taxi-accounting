from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from decimal import Decimal
from datetime import date, timedelta
import random

from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from accounts.models import SystemSettings


class Command(BaseCommand):
    help = 'Seed the database with sample data for all 4 operating models'

    def handle(self, *args, **options):
        random.seed(42)  # Reproducible results

        # ── 1. Superuser ──────────────────────────────────────────────
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@taxi.com', 'is_staff': True, 'is_superuser': True},
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('✓ Superuser created: admin / admin123'))
        else:
            self.stdout.write('  Superuser already exists')

        # ── 2. System Settings ────────────────────────────────────────
        settings, created = SystemSettings.objects.get_or_create(
            pk=1,
            defaults={
                'company_name': 'Maseru Transport Fleet',
                'company_phone': '+266 2232 0000',
                'company_email': 'info@maserutransport.co.ls',
                'company_address': 'Kingsway Road, Maseru, Lesotho',
                'debt_cap': Decimal('500.00'),
                'days_in_month_for_salary': 30,
            },
        )
        self.stdout.write(self.style.SUCCESS('✓ System settings ready'))

        # ── 3. Vehicles (one per operating model) ────────────────────
        vehicles_data = [
            {
                'name': 'Toyota Corolla-01',
                'vehicle_type': 'sedan',
                'seats': 4,
                'plate': 'A-1234',
                'operating_model': 'quota',
                'daily_quota': Decimal('250.00'),
                'insurance': Decimal('800.00'),
                'permit_cost': Decimal('1200.00'),
                'loan_payment': Decimal('1500.00'),
            },
            {
                'name': 'Toyota Hiace-01',
                'vehicle_type': 'minivan',
                'seats': 8,
                'plate': 'B-5678',
                'operating_model': 'salary',
                'monthly_salary': Decimal('3500.00'),
                'insurance': Decimal('1200.00'),
                'permit_cost': Decimal('1800.00'),
                'loan_payment': Decimal('2000.00'),
            },
            {
                'name': 'Nissan Caravan-01',
                'vehicle_type': 'minibus',
                'seats': 14,
                'plate': 'C-9012',
                'operating_model': 'percentage',
                'driver_percentage': Decimal('30.00'),
                'insurance': Decimal('1500.00'),
                'permit_cost': Decimal('2400.00'),
                'loan_payment': Decimal('2500.00'),
            },
            {
                'name': 'Toyota Coaster-01',
                'vehicle_type': 'bus',
                'seats': 30,
                'plate': 'D-3456',
                'operating_model': 'contract',
                'contract_target': Decimal('15000.00'),
                'contract_success_bonus_type': 'fixed',
                'contract_success_bonus_fixed': Decimal('2000.00'),
                'contract_success_bonus_percentage': Decimal('10.00'),
                'contract_failure_percentage': Decimal('20.00'),
                'insurance': Decimal('3000.00'),
                'permit_cost': Decimal('3600.00'),
                'loan_payment': Decimal('4000.00'),
            },
        ]

        created_vehicles = []
        for v in vehicles_data:
            plate = v['plate']
            obj, created = Vehicle.objects.get_or_create(plate=plate, defaults=v)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Vehicle created: {obj.name} ({obj.model_display})'))
            else:
                # Update fields in case they changed
                for key, val in v.items():
                    setattr(obj, key, val)
                obj.save()
                self.stdout.write(f'    Vehicle updated: {obj.name}')
            created_vehicles.append(obj)

        # ── 4. Drivers ────────────────────────────────────────────────
        drivers_data = [
            {
                'name': 'Thabo Mokoena',
                'phone': '+266 5012 3456',
                'vehicle_plate': 'A-1234',
                'portal_password': 'driver1',
            },
            {
                'name': 'Mpho Letsie',
                'phone': '+266 5012 3457',
                'vehicle_plate': 'B-5678',
                'portal_password': 'driver2',
            },
            {
                'name': 'Lerato Nkosi',
                'phone': '+266 5012 3458',
                'vehicle_plate': 'C-9012',
                'portal_password': 'driver3',
            },
            {
                'name': 'Tsepo Ramoholi',
                'phone': '+266 5012 3459',
                'vehicle_plate': 'D-3456',
                'portal_password': 'driver4',
            },
        ]

        created_drivers = []
        for d in drivers_data:
            vehicle = Vehicle.objects.get(plate=d['vehicle_plate'])
            obj, created = Driver.objects.get_or_create(
                phone=d['phone'],
                defaults={
                    'name': d['name'],
                    'vehicle': vehicle,
                    'portal_password': make_password(d['portal_password']),
                    'is_portal_enabled': True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Driver created: {obj.name}'))
            else:
                obj.name = d['name']
                obj.vehicle = vehicle
                obj.portal_password = make_password(d['portal_password'])
                obj.is_portal_enabled = True
                obj.save()
                self.stdout.write(f'    Driver updated: {obj.name}')
            created_drivers.append((obj, d['portal_password']))  # keep plain text for output

        # ── 5. Sample Settlements (7 days) ────────────────────────────
        today = date.today()
        settlement_count = 0

        for driver_obj, plain_pw in created_drivers:
            vehicle = driver_obj.vehicle
            for days_ago in range(7, 0, -1):
                sd = today - timedelta(days=days_ago)
                if sd.weekday() >= 5:  # skip weekends
                    continue
                if DailySettlement.objects.filter(driver=driver_obj, date=sd).exists():
                    continue

                # Base income varies by vehicle type
                if vehicle.vehicle_type == 'sedan':
                    base = random.uniform(300, 600)
                elif vehicle.vehicle_type == 'minivan':
                    base = random.uniform(500, 1000)
                elif vehicle.vehicle_type == 'minibus':
                    base = random.uniform(800, 1500)
                else:  # bus
                    base = random.uniform(1500, 3000)

                # For the quota driver, make one day below quota to show debt
                if vehicle.operating_model == 'quota' and days_ago == 3:
                    base = 150  # below 250 quota

                cash = Decimal(str(round(base * random.uniform(0.4, 0.7), 2)))
                mobile = Decimal(str(round(base * random.uniform(0.2, 0.4), 2)))
                card = Decimal(str(round(base * random.uniform(0.0, 0.2), 2)))
                fuel = Decimal(str(round(random.uniform(100, 300), 2)))
                toll = Decimal(str(round(random.uniform(20, 80), 2)))
                allowance = Decimal(str(round(random.uniform(50, 100), 2)))

                settlement = DailySettlement(
                    vehicle=vehicle,
                    driver=driver_obj,
                    date=sd,
                    cash_collected=cash,
                    mobile_collected=mobile,
                    card_collected=card,
                    fuel_cost=fuel,
                    toll_cost=toll,
                    driver_allowance=allowance,
                    payment_method='mixed',
                )
                settlement.save()
                settlement_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {settlement_count} settlements created'))

        # ── 6. Summary ────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═' * 50))
        self.stdout.write(self.style.SUCCESS('  ✅  Seed data complete!'))
        self.stdout.write(self.style.SUCCESS('═' * 50))
        self.stdout.write('')
        self.stdout.write('  Owner Portal:  http://localhost:8000/accounts/login/')
        self.stdout.write('    Username:  admin')
        self.stdout.write('    Password:  admin123')
        self.stdout.write('')
        self.stdout.write('  Driver Portal:  http://localhost:8000/driver/login/')
        for driver_obj, plain_pw in created_drivers:
            self.stdout.write(f'    {driver_obj.name}:  Code={driver_obj.driver_code}  Password={plain_pw}')
        self.stdout.write('')
        self.stdout.write('  Admin:  http://localhost:8000/admin/')
        self.stdout.write('    Username:  admin  Password:  admin123')
        self.stdout.write('')
        self.stdout.write(f'  Vehicles: {Vehicle.objects.count()}')
        self.stdout.write(f'  Drivers:  {Driver.objects.count()}')
        self.stdout.write(f'  Settlements: {DailySettlement.objects.count()}')