from django.urls import path, include
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='owner_dashboard'),

    # Loans
    path('loans/', include('loans.urls')),

    # Vehicles
    path('vehicles/', views.vehicle_list, name='owner_vehicle_list'),
    path('vehicles/add/', views.vehicle_add, name='owner_vehicle_add'),
    path('vehicles/<int:vehicle_id>/edit/', views.vehicle_edit, name='owner_vehicle_edit'),

    # Drivers
    path('drivers/', views.driver_list, name='owner_driver_list'),
    path('drivers/add/', views.driver_add, name='owner_driver_add'),
    path('drivers/<int:driver_id>/edit/', views.driver_edit, name='owner_driver_edit'),
    path('drivers/<int:driver_id>/settlements/', views.driver_settlements, name='owner_driver_settlements'),

    # Settlements
    path('settlements/', views.settlement_list, name='owner_settlement_list'),
    path('settlements/add/', views.settlement_add, name='owner_settlement_add'),
    path('settlements/<int:settlement_id>/', views.settlement_detail, name='owner_settlement_detail'),
    path('settlements/<int:settlement_id>/edit/', views.settlement_edit, name='owner_settlement_edit'),
    path('settlements/<int:settlement_id>/delete/', views.settlement_delete, name='owner_settlement_delete'),
    path('settlements/export/csv/', views.settlement_export_csv, name='owner_settlement_export'),

    # Approvals
    path('approvals/', views.pending_approvals, name='owner_pending_approvals'),
    path('approvals/<int:settlement_id>/review/', views.review_settlement, name='owner_review_settlement'),

    # Contracts
    path('contract/', views.contract_dashboard, name='owner_contract_dashboard'),
    path('contract/<int:driver_id>/', views.contract_detail, name='owner_contract_detail'),
    path('contract/<int:driver_id>/settle/', views.contract_settle, name='owner_contract_settle'),

    # Settings
    path('settings/', views.settings_view, name='owner_settings'),
    path('settings/update/', views.settings_update, name='owner_settings_update'),
]
