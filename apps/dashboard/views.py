# apps/dashboard/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.cache import never_cache
from .decorators import login_and_no_cache

@never_cache
def index_view(request):
    return render(request, 'index.html')

@login_and_no_cache
def admin_dashboard_view(request):
    return render(request, 'admin_dashboard.html')

@login_and_no_cache
def student_dashboard_view(request):
    return render(request, 'student_dashboard.html')

@never_cache
def logout_view(request):
    """
    Logout user and prevent back-button from showing previous pages.
    """
    logout(request)
    messages.success(request, "You have successfully logged out.")

    response = redirect('login')

    # Prevent caching
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

