"""
Seed data script for Taxi Accounting System.
Creates superuser, vehicles (all 4 models), drivers, and sample settlements.
Run: python manage.py shell < seed_data.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taxiaccounting.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from accounts.models import SystemSettings
from datetime import date, timedelta
import random

# Create superuser
if not User.objects.filter(username='tayloc').exists():
    User.objects.create_superuser('tayloc', 'admin@taxi.com', 'admin123')
    print('✓ Superuser created: tayloc / admin123')
else:
    print('✓ Superuser already exists')

# Create system settings
if not SystemSettings.objects.exists():
    SystemSettings.objects.create(
        company_name='Lesedy Logistics',
        company_phone='+266 2232 0000',
        company_email='info@lesedylogistics.co.ls',
        company_address='Maputsoe, Ha Maqele, Lesotho',
        debt_cap=500.00,
        days_in_month_for_salary=30,
    )
    print('✓ System settings created')
else:
    print('✓ System settings already exist')

# Create vehicles for each operating model


print('\n✅ Seed data creation complete!')
print('\n--- Login Credentials ---')
print('Owner Portal: http://localhost:8000/accounts/login/')
print('  Username: admin')
print('  Password: admin123')
print('\nDriver Portal: http://localhost:8000/driver/login/')
print('\nAdmin: http://localhost:8000/admin/')
print('  Username: admin, Password: admin123')