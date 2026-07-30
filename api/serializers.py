from rest_framework import serializers
from vehicles.models import Vehicle
from drivers.models import Driver
from settlements.models import DailySettlement
from contracts.models import MonthlyContractSummary

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'

class DriverContractSerializer(serializers.Serializer):
    target = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_gross = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining_target = serializers.DecimalField(max_digits=12, decimal_places=2)
    progress = serializers.DecimalField(max_digits=5, decimal_places=2)
    bonus_type = serializers.CharField()
    success_bonus_fixed = serializers.DecimalField(max_digits=10, decimal_places=2)
    success_bonus_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    failure_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)

class DailySettlementSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    vehicle_name = serializers.CharField(source='vehicle.name', read_only=True)
    
    class Meta:
        model = DailySettlement
        fields = '__all__'

class MonthlyContractSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyContractSummary
        fields = '__all__'