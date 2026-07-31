"""
API views for the Taxi Accounting System.
Provides JSON endpoints for AJAX calls and external integrations.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import date
import calendar

from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from contracts.models import MonthlyContractSummary
from .serializers import (
    VehicleSerializer, DriverSerializer,
    DailySettlementSerializer, MonthlyContractSummarySerializer,
)


class VehicleViewSet(viewsets.ModelViewSet):
    """API endpoint for vehicles."""
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]


class DriverViewSet(viewsets.ModelViewSet):
    """API endpoint for drivers."""
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated]


class DailySettlementViewSet(viewsets.ModelViewSet):
    """API endpoint for settlements."""
    queryset = DailySettlement.objects.all()
    serializer_class = DailySettlementSerializer
    permission_classes = [permissions.IsAuthenticated]


class MonthlyContractSummaryViewSet(viewsets.ModelViewSet):
    """API endpoint for contract summaries."""
    queryset = MonthlyContractSummary.objects.all()
    serializer_class = MonthlyContractSummarySerializer
    permission_classes = [permissions.IsAuthenticated]


# ------------------------------------------------------------------
# Custom API endpoints
# ------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def vehicle_details(request, vehicle_id):
    """Return vehicle details including model-specific parameters."""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    data = {
        'id': vehicle.id,
        'name': vehicle.name,
        'plate': vehicle.plate,
        'vehicle_type': vehicle.vehicle_type,
        'vehicle_type_display': vehicle.get_vehicle_type_display(),
        'operating_model': vehicle.operating_model,
        'operating_model_display': vehicle.model_display,
        'seats': vehicle.seats,
        'daily_quota': str(vehicle.daily_quota),
        'monthly_salary': str(vehicle.monthly_salary),
        'driver_percentage': str(vehicle.driver_percentage),
        'contract_target': str(vehicle.contract_target),
        'contract_success_bonus_type': vehicle.contract_success_bonus_type,
        'contract_success_bonus_fixed': str(vehicle.contract_success_bonus_fixed),
        'contract_success_bonus_percentage': str(vehicle.contract_success_bonus_percentage),
        'contract_failure_percentage': str(vehicle.contract_failure_percentage),
        'insurance': str(vehicle.insurance),
        'permit_cost': str(vehicle.permit_cost),
        'loan_payment': str(vehicle.loan_payment),
        'monthly_fixed_costs': str(vehicle.monthly_fixed_costs),
        'default_settlement_frequency': vehicle.default_settlement_frequency,
    }
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def vehicle_drivers(request, vehicle_id):
    """List active drivers for a vehicle."""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    drivers = vehicle.drivers.filter(is_active=True)
    data = [
        {
            'id': d.id,
            'name': d.name,
            'phone': d.phone,
            'driver_code': d.driver_code,
            'is_portal_enabled': d.is_portal_enabled,
        }
        for d in drivers
    ]
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def driver_details(request, driver_id):
    """Return driver details including debt balance and contract progress."""
    driver = get_object_or_404(Driver, id=driver_id)
    data = {
        'id': driver.id,
        'name': driver.name,
        'phone': driver.phone,
        'email': driver.email,
        'driver_code': driver.driver_code,
        'is_portal_enabled': driver.is_portal_enabled,
        'vehicle': driver.vehicle.name if driver.vehicle else None,
        'operating_model': driver.vehicle.operating_model if driver.vehicle else None,
        'model_display': driver.model_display,
        'debt_balance': str(driver.debt_balance),
        'effective_quota': str(driver.effective_quota),
        'effective_salary': str(driver.effective_salary),
        'effective_percentage': str(driver.effective_percentage),
        'effective_contract_target': str(driver.effective_contract_target),
    }
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def driver_contract(request, driver_id):
    """Return contract progress for a driver."""
    driver = get_object_or_404(Driver, id=driver_id)

    if not driver.vehicle or driver.vehicle.operating_model != 'contract':
        return Response({'error': 'Driver is not on a contract model'}, status=status.HTTP_400_BAD_REQUEST)

    today = date.today()
    month_start = today.replace(day=1)
    _, days_in_month = calendar.monthrange(today.year, today.month)

    settlements = driver.settlements.filter(
        status='approved', operating_model='contract',
        date__year=today.year, date__month=today.month
    )
    monthly_gross = sum(s.total_income for s in settlements)
    target = driver.effective_contract_target
    progress = (monthly_gross / target * 100) if target > 0 else 0
    days_remaining = days_in_month - today.day
    daily_needed = max(0, (target - monthly_gross) / max(1, days_remaining)) if days_remaining > 0 else 0

    data = {
        'driver_id': driver.id,
        'driver_name': driver.name,
        'target': str(target),
        'monthly_gross': str(monthly_gross),
        'remaining_target': str(max(0, target - monthly_gross)),
        'progress': round(progress, 2),
        'days_remaining': days_remaining,
        'daily_average_needed': str(daily_needed),
        'bonus_type': driver.vehicle.contract_success_bonus_type,
        'success_bonus_fixed': str(driver.effective_contract_success_bonus_fixed),
        'success_bonus_percentage': str(driver.effective_contract_success_bonus_percentage),
        'failure_percentage': str(driver.effective_contract_failure_percentage),
    }
    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def driver_login(request):
    """API endpoint for driver login."""
    driver_code = request.data.get('driver_code', '')
    password = request.data.get('password', '')

    try:
        driver = Driver.objects.get(driver_code=driver_code, is_portal_enabled=True)
    except Driver.DoesNotExist:
        return Response({'error': 'Invalid driver code'}, status=status.HTTP_401_UNAUTHORIZED)

    if driver.check_portal_password(password):
        return Response({
            'success': True,
            'driver_id': driver.id,
            'driver_name': driver.name,
            'vehicle': driver.vehicle.name if driver.vehicle else None,
            'operating_model': driver.vehicle.operating_model if driver.vehicle else None,
        })
    return Response({'error': 'Invalid password'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def contract_summary(request):
    """Return a summary of all contract drivers' progress."""
    today = date.today()
    contract_drivers = Driver.objects.filter(
        vehicle__operating_model='contract', is_active=True
    ).select_related('vehicle')

    data = []
    for driver in contract_drivers:
        settlements = driver.settlements.filter(
            status='approved', operating_model='contract',
            date__year=today.year, date__month=today.month
        )
        monthly_gross = sum(s.total_income for s in settlements)
        target = driver.effective_contract_target
        progress = (monthly_gross / target * 100) if target > 0 else 0

        data.append({
            'driver_id': driver.id,
            'driver_name': driver.name,
            'vehicle': driver.vehicle.name,
            'target': str(target),
            'monthly_gross': str(monthly_gross),
            'progress': round(progress, 2),
            'is_on_track': progress >= 100,
        })

    return Response(data)
