"""
Account views – authentication and user management.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout
from django.contrib import messages


def login(request):
    """Owner login – uses Django's built-in auth views via URL config."""
    from django.contrib.auth.views import LoginView
    return LoginView.as_view(template_name='accounts/login.html')(request)


def logout(request):
    """Owner logout – clears the session and redirects to the login page."""
    auth_logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')
