from django.urls import path
from . import views

urlpatterns = [
    # Cash book dashboard and entries
    path('', views.cashbook_dashboard, name='owner_cashbook_dashboard'),
    path('entries/', views.cashbook_entries, name='owner_cashbook_entries'),
    path('ledger/', views.cashbook_ledger, name='owner_cashbook_ledger'),
    path('add/', views.cashbook_add, name='owner_cashbook_add'),
    path('<int:transaction_id>/edit/', views.cashbook_edit, name='owner_cashbook_edit'),
    path('<int:transaction_id>/delete/', views.cashbook_delete, name='owner_cashbook_delete'),
    path('entries/export/csv/', views.cashbook_export_csv, name='owner_cashbook_export'),

    # Bank accounts
    path('banks/', views.bank_list, name='owner_cashbook_banks'),
    path('banks/add/', views.bank_add, name='owner_cashbook_bank_add'),
    path('banks/<int:bank_id>/edit/', views.bank_edit, name='owner_cashbook_bank_edit'),
    path('banks/<int:bank_id>/delete/', views.bank_delete, name='owner_cashbook_bank_delete'),
    path('transfer-to-bank/', views.bank_deposit, name='owner_cashbook_bank_deposit'),
    path('transfer-from-bank/', views.bank_withdraw, name='owner_cashbook_bank_withdraw'),

    # Expenses and petty cash
    path('expense/', views.record_expense, name='owner_cashbook_expense'),
    path('petty-cash/', views.record_petty_cash, name='owner_cashbook_petty_cash'),
]