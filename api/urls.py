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
    path('driver/<int:driver_id>/contract/', views.driver_contract_progress, name='api_driver_contract'),
    path('driver/login/', views.driver_login, name='api_driver_login'),
    path('contract/summary/', views.contract_summary, name='api_contract_summary'),
]