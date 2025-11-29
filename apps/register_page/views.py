# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.utils import timezone
import re

from apps.register_page.models import AdminProfile, StudentProfile

EMAIL_DOMAIN = '@cit.edu'

def register_choice(request):
    """Display registration type choice page"""
    return render(request, 'register_choice.html')

def register_student(request):
    """Handle student registration"""
    if request.method != 'POST':
        return render(request, 'register_student.html')

    email = request.POST.get('email')
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')
    name = request.POST.get('name')
    cit_id = request.POST.get('cit_id')

    if not all([email, password, cit_id, name]):
        messages.error(request, 'Please fill out all required fields.')
        return render(request, 'register_student.html')

    if password != confirm_password:
        messages.error(request, 'Passwords do not match.')
        return render(request, 'register_student.html')

    if not (len(password) >= 8 and re.search(r'[A-Z]', password)
            and re.search(r'[a-z]', password) and re.search(r'\d', password)):
        messages.error(request, 'Password must be at least 8 characters with uppercase, lowercase, and number.')
        return render(request, 'register_student.html')

    if not email.endswith(EMAIL_DOMAIN):
        messages.error(request, f'Registration is limited to {EMAIL_DOMAIN} email addresses only.')
        return render(request, 'register_student.html')

    if not re.fullmatch(r'^[0-9-]+$', cit_id):
        messages.error(request, 'Student ID can only contain numbers and dashes (-).')
        return render(request, 'register_student.html')

    # Uniqueness checks
    if User.objects.filter(username=email).exists():
        messages.error(request, 'A user with this email already exists.')
        return render(request, 'register_student.html')

    if StudentProfile.objects.filter(cit_id=cit_id).exists() or AdminProfile.objects.filter(cit_id=cit_id).exists():
        messages.error(request, 'This Student ID is already registered.')
        return render(request, 'register_student.html')

    # Create student user
    try:
        user = User.objects.create_user(
            username=email, 
            email=email, 
            password=password, 
            is_staff=False
        )

        StudentProfile.objects.create(
            user=user,
            name=name,
            cit_id=cit_id,
            created_at=timezone.now()
        )

        logged_in_user = authenticate(request, username=email, password=password)
        login(request, logged_in_user)
        messages.success(request, 'Student registration successful! You are now logged in.')
        return redirect('student_dashboard')

    except Exception as e:
        if user:
            try:
                user.delete()
            except:
                pass
        messages.error(request, f'Registration failed: {str(e)}')
        return render(request, 'register_student.html')

def register_administrator(request):
    """Handle administrator registration"""
    if request.method != 'POST':
        return render(request, 'register_administrator.html')

    email = request.POST.get('email')
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')
    name = request.POST.get('name')
    cit_id = request.POST.get('cit_id')
    organization_name = request.POST.get('organization_name')

    if not all([email, password, cit_id, name, organization_name]):
        messages.error(request, 'Please fill out all required fields.')
        return render(request, 'register_administrator.html')

    if password != confirm_password:
        messages.error(request, 'Passwords do not match.')
        return render(request, 'register_administrator.html')

    if not (len(password) >= 8 and re.search(r'[A-Z]', password)
            and re.search(r'[a-z]', password) and re.search(r'\d', password)):
        messages.error(request, 'Password must be at least 8 characters with uppercase, lowercase, and number.')
        return render(request, 'register_administrator.html')

    if not email.endswith(EMAIL_DOMAIN):
        messages.error(request, f'Registration is limited to {EMAIL_DOMAIN} email addresses only.')
        return render(request, 'register_administrator.html')

    if not re.fullmatch(r'^[0-9-]+$', cit_id):
        messages.error(request, 'Employee ID can only contain numbers and dashes (-).')
        return render(request, 'register_administrator.html')

    # Uniqueness checks
    if User.objects.filter(username=email).exists():
        messages.error(request, 'A user with this email already exists.')
        return render(request, 'register_administrator.html')

    if StudentProfile.objects.filter(cit_id=cit_id).exists() or AdminProfile.objects.filter(cit_id=cit_id).exists():
        messages.error(request, 'This Employee ID is already registered.')
        return render(request, 'register_administrator.html')

    if AdminProfile.objects.filter(organization_name=organization_name).exists():
        messages.error(request, f'The organization "{organization_name}" already has an assigned administrator.')
        return render(request, 'register_administrator.html')

    # Create administrator user
    try:
        user = User.objects.create_user(
            username=email, 
            email=email, 
            password=password, 
            is_staff=True
        )

        AdminProfile.objects.create(
            user=user,
            name=name,
            cit_id=cit_id,
            organization_name=organization_name,
            created_at=timezone.now()
        )

        logged_in_user = authenticate(request, username=email, password=password)
        login(request, logged_in_user)
        messages.success(request, 'Organizer registration successful! You are now logged in.')
        return redirect('admin_dashboard')

    except Exception as e:
        if user:
            try:
                user.delete()
            except:
                pass
        messages.error(request, f'Registration failed: {str(e)}')
        return render(request, 'register_administrator.html')