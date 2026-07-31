from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'vehicles', views.VehicleViewSet)
router.register(r'drivers', views.DriverViewSet)
router.register(r'settlements', views.DailySettlementViewSet)
router.register(r'contract-summaries', views.MonthlyContractSummaryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('vehicle/<int:vehicle_id>/details/', views.vehicle_details, name='api_vehicle_details'),
    path('vehicle/<int:vehicle_id>/drivers/', views.vehicle_drivers, name='api_vehicle_drivers'),
    path('driver/<int:driver_id>/details/', views.driver_details, name='api_driver_details'),
    path('driver/<int:driver_id>/contract/', views.driver_contract, name='api_driver_contract'),
    path('driver/login/', views.driver_login, name='api_driver_login'),
    path('contract/summary/', views.contract_summary, name='api_contract_summary'),
]
