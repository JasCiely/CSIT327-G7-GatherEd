from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.utils import timezone
import re

from apps.register_page.models import AdminProfile, StudentProfile

EMAIL_DOMAIN = '@cit.edu'

def register(request):
    if request.method != 'POST':
        return render(request, 'register.html')

    email = request.POST.get('email')
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')
    name = request.POST.get('name')
    user_type = request.POST.get('user_type')
    cit_id = request.POST.get('cit_id')
    organization_name = request.POST.get('organization_name')

    if not all([email, password, cit_id, name, user_type]):
        messages.error(request, 'Please fill out all required fields.')
        return render(request, 'register.html')

    if password != confirm_password:
        messages.error(request, 'Passwords do not match.')
        return render(request, 'register.html')

    if user_type == 'administrator' and not organization_name:
        messages.error(request, 'Administrator registration requires an Organization Affiliation.')
        return render(request, 'register.html')

    if not (len(password) >= 8 and re.search(r'[A-Z]', password)
            and re.search(r'[a-z]', password) and re.search(r'\d', password)):
        messages.error(request, 'Password must meet complexity requirements.')
        return render(request, 'register.html')

    if not email.endswith(EMAIL_DOMAIN):
        messages.error(request, f'Registration is limited to {EMAIL_DOMAIN} email addresses only.')
        return render(request, 'register.html')

    if not re.fullmatch(r'^[0-9-]+$', cit_id):
        messages.error(request, 'CIT ID can only contain numbers and dashes (-).')
        return render(request, 'register.html')

    # Uniqueness checks
    if User.objects.filter(username=email).exists():
        messages.error(request, 'A user with this email already exists.')
        return render(request, 'register.html')

    if StudentProfile.objects.filter(cit_id=cit_id).exists() or AdminProfile.objects.filter(cit_id=cit_id).exists():
        messages.error(request, 'This CIT ID is already registered.')
        return render(request, 'register.html')

    if user_type == 'administrator' and AdminProfile.objects.filter(organization_name=organization_name).exists():
        messages.error(request, f'The organization "{organization_name}" already has an assigned administrator.')
        return render(request, 'register.html')

    # Create user
    try:
        is_staff_user = (user_type == 'administrator')
        user = User.objects.create_user(username=email, email=email, password=password, is_staff=is_staff_user)

        if user_type == 'administrator':
            AdminProfile.objects.create(
                user=user,
                name=name,
                cit_id=cit_id,
                organization_name=organization_name,
                created_at=timezone.now()
            )
            redirect_path = 'admin_dashboard'
        else:
            StudentProfile.objects.create(
                user=user,
                name=name,
                cit_id=cit_id,
                created_at=timezone.now()
            )
            redirect_path = 'student_dashboard'

        logged_in_user = authenticate(request, username=email, password=password)
        login(request, logged_in_user)
        messages.success(request, 'Registration successful! You are now logged in.')
        return redirect(redirect_path)

    except Exception as e:
        if user:
            try:
                user.delete()
            except:
                pass
        messages.error(request, f'Registration failed: {str(e)}')
        return render(request, 'register.html')
