from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='driver_login'),
    path('logout/', views.logout, name='driver_logout'),
    path('dashboard/', views.dashboard, name='driver_dashboard'),

    # Settlements
    path('settlements/', views.settlements, name='driver_settlements'),
    path('settlements/create/', views.settlement_create, name='driver_settlement_create'),
    path('settlements/<int:settlement_id>/view/', views.settlement_view, name='driver_settlement_view'),
    path('settlements/<int:settlement_id>/edit/', views.settlement_edit, name='driver_settlement_edit'),
    path('settlements/<int:settlement_id>/print/', views.settlement_print, name='driver_settlement_print'),

    # Contract & debt
    path('contract/', views.contract, name='driver_contract'),
    path('debt/', views.debt, name='driver_debt'),

    # Loans
    path('loans/', views.loans, name='driver_loans'),

    # Profile
    path('profile/', views.profile, name='driver_profile'),
    path('change-password/', views.change_password, name='driver_change_password'),
]
