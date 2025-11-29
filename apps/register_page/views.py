# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import re

from apps.register_page.models import AdminProfile, StudentProfile
from apps.register_page.utils import send_otp_email

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
    user = None
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
    """Handle administrator registration - Step 1: Create account"""
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

    # Check if organization already has a VERIFIED administrator
    verified_admin_exists = AdminProfile.objects.filter(
        organization_name=organization_name,
        is_verified=True
    ).exists()

    if verified_admin_exists:
        messages.error(request, f'The organization "{organization_name}" already has a verified administrator. Please contact the existing administrator or choose a different organization.')
        return render(request, 'register_administrator.html')

    # Create administrator user
    user = None
    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_staff=True,
            is_active=False  # Deactivate until verified
        )

        admin_profile = AdminProfile.objects.create(
            user=user,
            name=name,
            cit_id=cit_id,
            organization_name=organization_name,
            is_verified=False,
            created_at=timezone.now()
        )

        # Store user ID in session for OTP verification
        request.session['pending_admin_id'] = user.id
        request.session['pending_admin_email'] = email

        # Send OTP email
        email_sent = send_otp_email(admin_profile, request)

        if email_sent:
            messages.info(
                request,
                f'Verification code sent to {email}. Please check your email and enter the code below.'
            )
            return redirect('verify_otp')
        else:
            messages.error(
                request,
                'Account created but failed to send verification email. Please try again.'
            )
            # Clean up if email fails
            user.delete()
            return render(request, 'register_administrator.html')

    except Exception as e:
        if user:
            try:
                user.delete()
            except:
                pass
        messages.error(request, f'Registration failed: {str(e)}')
        return render(request, 'register_administrator.html')


def verify_otp(request):
    """Handle OTP verification - Step 2: Verify account"""
    if request.method == 'GET':
        # Check if there's a pending admin verification
        if 'pending_admin_id' not in request.session:
            messages.error(request, 'No pending verification found. Please register first.')
            return redirect('register_administrator')
        return render(request, 'verify_otp.html')

    elif request.method == 'POST':
        # Verify OTP code
        entered_otp = request.POST.get('otp_code')
        pending_admin_id = request.session.get('pending_admin_id')

        if not entered_otp:
            messages.error(request, 'Please enter the verification code.')
            return render(request, 'verify_otp.html')

        if not pending_admin_id:
            messages.error(request, 'Session expired. Please register again.')
            return redirect('register_administrator')

        try:
            admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)

            if admin_profile.is_otp_expired():
                messages.error(request, 'Verification code has expired. Please register again.')
                # Clean up expired registration
                admin_profile.user.delete()
                request.session.flush()
                return redirect('register_administrator')

            if admin_profile.otp_code == entered_otp:
                # Check if organization was taken by another verified admin during OTP process
                verified_admin_exists = AdminProfile.objects.filter(
                    organization_name=admin_profile.organization_name,
                    is_verified=True
                ).exclude(id=admin_profile.id).exists()

                if verified_admin_exists:
                    messages.error(
                        request,
                        f'This organization "{admin_profile.organization_name}" has been assigned to another administrator during the verification process. Please register with a different organization.'
                    )
                    # Clean up this registration
                    admin_profile.user.delete()
                    request.session.flush()
                    return redirect('register_administrator')

                # OTP verified successfully
                admin_profile.is_verified = True
                admin_profile.otp_code = None
                admin_profile.otp_created_at = None
                admin_profile.save()

                admin_profile.user.is_active = True
                admin_profile.user.save()

                # Clean up any other unverified admins for this organization
                AdminProfile.objects.filter(
                    organization_name=admin_profile.organization_name,
                    is_verified=False
                ).exclude(id=admin_profile.id).delete()

                # Log the user in
                login(request, admin_profile.user)

                # Clean up session
                request.session.flush()

                messages.success(request, 'Account verified successfully! You are now logged in.')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Invalid verification code. Please try again.')
                return render(request, 'verify_otp.html')

        except AdminProfile.DoesNotExist:
            messages.error(request, 'Admin profile not found. Please register again.')
            request.session.flush()
            return redirect('register_administrator')


def resend_otp(request):
    """Resend OTP verification code"""
    pending_admin_id = request.session.get('pending_admin_id')

    if not pending_admin_id:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register_administrator')

    try:
        admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)

        if admin_profile.is_verified:
            messages.info(request, 'Your account is already verified.')
            return redirect('admin_dashboard')

        # Check if organization was taken by another verified admin
        verified_admin_exists = AdminProfile.objects.filter(
            organization_name=admin_profile.organization_name,
            is_verified=True
        ).exclude(id=admin_profile.id).exists()

        if verified_admin_exists:
            messages.error(
                request,
                f'This organization "{admin_profile.organization_name}" has been assigned to another administrator. Please register with a different organization.'
            )
            # Clean up this registration
            admin_profile.user.delete()
            request.session.flush()
            return redirect('register_administrator')

        # Generate and send new OTP
        email_sent = send_otp_email(admin_profile, request)

        if email_sent:
            messages.success(request, 'New verification code sent! Please check your email.')
        else:
            messages.error(request, 'Failed to send verification code. Please try again.')

        return redirect('verify_otp')

    except AdminProfile.DoesNotExist:
        messages.error(request, 'Admin profile not found. Please register again.')
        request.session.flush()
        return redirect('register_administrator')