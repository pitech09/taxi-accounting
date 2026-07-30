from django.urls import path
from . import views

urlpatterns = [
    path('contract-progress/', views.contract_progress, name='report_contract_progress'),
    path('contract-settlements/', views.contract_settlements, name='report_contract_settlements'),
    path('contract-analytics/', views.contract_analytics, name='report_contract_analytics'),

    # Cash book reports
    path('cashbook/', views.cashbook_report, name='report_cashbook'),
    path('cashbook/export/csv/', views.cashbook_report_csv, name='report_cashbook_csv'),
    path('bank-reconciliation/', views.bank_reconciliation, name='report_bank_reconciliation'),
    path('expenses/', views.expense_report, name='report_expenses'),
    path('cash-flow/', views.cash_flow_report, name='report_cash_flow'),
]