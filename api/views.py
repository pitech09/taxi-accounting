from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, timedelta
from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from contracts.models import MonthlyContractSummary
from .serializers import (
    VehicleSerializer, DriverSerializer, DailySettlementSerializer,
    MonthlyContractSummarySerializer, DriverContractSerializer
)

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer

class DailySettlementViewSet(viewsets.ModelViewSet):
    queryset = DailySettlement.objects.all()
    serializer_class = DailySettlementSerializer

class MonthlyContractSummaryViewSet(viewsets.ModelViewSet):
    queryset = MonthlyContractSummary.objects.all()
    serializer_class = MonthlyContractSummarySerializer

@api_view(['GET'])
@permission_classes([AllowAny])
def driver_contract_progress(request, driver_id):
    """Get contract progress data for a driver"""
    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return Response({'error': 'Driver not found'}, status=404)
    
    if not driver.vehicle or driver.vehicle.operating_model != 'contract':
        return Response({'error': 'Driver not on contract model'}, status=400)
    
    today = date.today()
    month_start = today.replace(day=1)
    
    settlements = DailySettlement.objects.filter(
        driver=driver,
        date__gte=month_start,
        date__lte=today,
        operating_model='contract'
    )
    
    monthly_gross = sum(s.total_income for s in settlements)
    target = driver.effective_contract_target
    remaining = max(0, target - monthly_gross)
    progress = min(100, (monthly_gross / target * 100)) if target > 0 else 0
    
    data = {
        'target': target,
        'monthly_gross': monthly_gross,
        'remaining_target': remaining,
        'progress': progress,
        'bonus_type': driver.vehicle.contract_success_bonus_type,
        'success_bonus_fixed': driver.effective_contract_success_bonus_fixed,
        'success_bonus_percentage': driver.effective_contract_success_bonus_percentage,
        'failure_percentage': driver.effective_contract_failure_percentage,
    }
    
    return Response(data)

@api_view(['POST'])
@permission_classes([AllowAny])
def driver_login(request):
    """Simple driver portal login using driver_code"""
    driver_code = request.data.get('driver_code')
    password = request.data.get('password')
    
    try:
        driver = Driver.objects.get(driver_code=driver_code, is_portal_enabled=True)
        if driver.portal_password == password:
            driver.last_login = timezone.now()
            driver.save()
            return Response({
                'success': True,
                'driver_id': driver.id,
                'driver_code': driver.driver_code,
                'driver_name': driver.name
            })
    except Driver.DoesNotExist:
        pass
    
    return Response({'success': False, 'error': 'Invalid credentials'}, status=401)

@api_view(['GET'])
@permission_classes([AllowAny])
def contract_summary(request):
    """Get summary of all active contracts"""
    today = date.today()
    month_start = today.replace(day=1)
    
    contract_drivers = Driver.objects.filter(
        vehicle__operating_model='contract',
        is_active=True
    )
    
    summaries = []
    for driver in contract_drivers:
        settlements = DailySettlement.objects.filter(
            driver=driver,
            date__gte=month_start,
            date__lte=today,
            operating_model='contract'
        )
        monthly_gross = sum(s.total_income for s in settlements)
        target = driver.effective_contract_target
        progress = min(100, (monthly_gross / target * 100)) if target > 0 else 0
        
        if progress >= 100:
            status_label = 'Achieved'
        elif progress >= 70:
            status_label = 'On Track'
        else:
            status_label = 'At Risk'
        
        summaries.append({
            'driver_id': driver.id,
            'driver_name': driver.name,
            'vehicle_name': driver.vehicle.name if driver.vehicle else 'N/A',
            'target': target,
            'monthly_gross': monthly_gross,
            'progress': progress,
            'status': status_label,
        })
    
    return Response(summaries)