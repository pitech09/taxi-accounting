from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    path('', views.loan_list, name='loan_list'),
    path('add/', views.loan_add, name='loan_add'),
    path('<int:loan_id>/', views.loan_detail, name='loan_detail'),
    path('<int:loan_id>/pay/', views.loan_pay, name='loan_pay'),
    path('<int:loan_id>/accrue-interest/', views.loan_accrue_interest, name='loan_accrue_interest'),
]