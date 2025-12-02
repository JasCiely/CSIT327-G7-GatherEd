from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import re

from apps.register_page.models import AdminProfile, StudentProfile
from apps.register_page.utils import send_otp_email, send_student_otp_email

EMAIL_DOMAIN = '@cit.edu'


def register_choice(request):
    """Display registration type choice page"""
    return render(request, 'register_choice.html')


def register_student(request):
    """Handle student registration with OTP verification"""
    # Reset OTP resend count when starting new registration
    if 'student_otp_resend_count' in request.session:
        del request.session['student_otp_resend_count']

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
            is_staff=False,
            is_active=False  # Deactivate until verified
        )

        student_profile = StudentProfile.objects.create(
            user=user,
            name=name,
            cit_id=cit_id,
            is_verified=False,  # Add this
            created_at=timezone.now()
        )

        # Store user ID in session for OTP verification
        request.session['pending_student_id'] = user.id
        request.session['pending_student_email'] = email

        # Initialize OTP resend counter
        request.session['student_otp_resend_count'] = 0

        # Send OTP email
        email_sent = send_student_otp_email(student_profile, request)

        if email_sent:
            messages.info(
                request,
                f'Verification code sent to {email}. Please check your email and enter the code within 10 minutes.'
            )
            return redirect('verify_student_otp')
        else:
            messages.error(
                request,
                'Account created but failed to send verification email. Please try again.'
            )
            # Clean up if email fails
            user.delete()
            return render(request, 'register_student.html')

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
    # Reset OTP resend count when starting new registration
    if 'otp_resend_count' in request.session:
        del request.session['otp_resend_count']

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
        messages.error(request,
                       f'The organization "{organization_name}" already has a verified administrator. Please contact the existing administrator or choose a different organization.')
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

        # Initialize OTP resend counter
        request.session['otp_resend_count'] = 0

        # Send OTP email
        email_sent = send_otp_email(admin_profile, request)

        if email_sent:
            messages.info(
                request,
                f'Verification code sent to {email}. Please check your email and enter the code within 10 minutes.'
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


def cleanup_pending_registration(request):
    """Clean up pending registration when user goes back"""
    pending_admin_id = request.session.get('pending_admin_id')

    if pending_admin_id:
        try:
            # Get the admin profile and user
            admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)
            user = admin_profile.user

            # Delete both the profile and user
            admin_profile.delete()
            user.delete()

            # Clear session data
            if 'pending_admin_id' in request.session:
                del request.session['pending_admin_id']
            if 'pending_admin_email' in request.session:
                del request.session['pending_admin_email']
            if 'otp_resend_count' in request.session:
                del request.session['otp_resend_count']

            messages.info(request, 'Registration cancelled. You can start a new registration.')

        except (AdminProfile.DoesNotExist, User.DoesNotExist):
            # If the objects don't exist, just clear the session
            if 'pending_admin_id' in request.session:
                del request.session['pending_admin_id']
            if 'pending_admin_email' in request.session:
                del request.session['pending_admin_email']
            if 'otp_resend_count' in request.session:
                del request.session['otp_resend_count']

    return redirect('register_administrator')


def cleanup_pending_student_registration(request):
    """Clean up pending student registration when user goes back"""
    pending_student_id = request.session.get('pending_student_id')

    if pending_student_id:
        try:
            # Get the student profile and user
            student_profile = StudentProfile.objects.get(user_id=pending_student_id)
            user = student_profile.user

            # Delete both the profile and user
            student_profile.delete()
            user.delete()

            # Clear session data
            if 'pending_student_id' in request.session:
                del request.session['pending_student_id']
            if 'pending_student_email' in request.session:
                del request.session['pending_student_email']
            if 'student_otp_resend_count' in request.session:
                del request.session['student_otp_resend_count']

            messages.info(request, 'Registration cancelled. You can start a new registration.')

        except (StudentProfile.DoesNotExist, User.DoesNotExist):
            # If the objects don't exist, just clear the session
            if 'pending_student_id' in request.session:
                del request.session['pending_student_id']
            if 'pending_student_email' in request.session:
                del request.session['pending_student_email']
            if 'student_otp_resend_count' in request.session:
                del request.session['student_otp_resend_count']

    return redirect('register_student')


def cleanup_and_register(request):
    """Clean up and redirect to registration page"""
    return cleanup_pending_registration(request)


def verify_otp(request):
    """Handle OTP verification - Step 2: Verify account"""
    if request.method == 'GET':
        # Check if there's a pending admin verification
        if 'pending_admin_id' not in request.session:
            messages.error(request, 'No pending verification found. Please register first.')
            return redirect('register_administrator')

        # Calculate remaining time for the current OTP
        remaining_time = 0
        is_otp_expired = False
        try:
            admin_profile = AdminProfile.objects.get(user_id=request.session.get('pending_admin_id'))
            if admin_profile.otp_created_at:
                elapsed_time = (timezone.now() - admin_profile.otp_created_at).total_seconds()
                remaining_time = max(0, 600 - int(elapsed_time))
                is_otp_expired = elapsed_time >= 600
        except AdminProfile.DoesNotExist:
            # If admin profile doesn't exist, cleanup and redirect
            cleanup_pending_registration(request)
            messages.error(request, 'Registration session expired. Please register again.')
            return redirect('register_administrator')

        return render(request, 'verify_otp.html', {
            'remaining_time': remaining_time,
            'is_otp_expired': is_otp_expired
        })

    elif request.method == 'POST':
        # Verify OTP code
        entered_otp = request.POST.get('otp_code')
        pending_admin_id = request.session.get('pending_admin_id')

        if not entered_otp:
            messages.error(request, 'Please enter the verification code.')
            # Calculate remaining time for error case
            remaining_time = 0
            is_otp_expired = False
            try:
                admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)
                if admin_profile.otp_created_at:
                    elapsed_time = (timezone.now() - admin_profile.otp_created_at).total_seconds()
                    remaining_time = max(0, 600 - int(elapsed_time))
                    is_otp_expired = elapsed_time >= 600
            except AdminProfile.DoesNotExist:
                cleanup_pending_registration(request)
                messages.error(request, 'Registration session expired. Please register again.')
                return redirect('register_administrator')
            return render(request, 'verify_otp.html', {
                'remaining_time': remaining_time,
                'is_otp_expired': is_otp_expired
            })

        if not pending_admin_id:
            messages.error(request, 'Session expired. Please register again.')
            return redirect('register_administrator')

        try:
            admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)

            # Check if OTP is expired first
            if admin_profile.is_otp_expired():
                messages.error(request,
                               'Verification code has expired. Please request a new code using the "Resend Code" link.')
                return render(request, 'verify_otp.html', {
                    'remaining_time': 0,
                    'is_otp_expired': True
                })

            # Then check if OTP is correct
            if admin_profile.otp_code == entered_otp:
                # OTP verified successfully
                admin_profile.is_verified = True
                admin_profile.otp_code = None
                admin_profile.otp_created_at = None
                admin_profile.save()

                admin_profile.user.is_active = True
                admin_profile.user.save()

                # Clean up session including resend counter
                request.session.flush()

                messages.success(request, 'Account verified successfully! Please log in to continue.')
                return redirect('login')
            else:
                # OTP is incorrect but still valid (not expired)
                # Calculate remaining time for the current OTP
                elapsed_time = (timezone.now() - admin_profile.otp_created_at).total_seconds()
                remaining_time = max(0, 600 - int(elapsed_time))
                is_otp_expired = elapsed_time >= 600

                messages.error(request, 'Invalid verification code. Please try again with the same code.')
                return render(request, 'verify_otp.html', {
                    'remaining_time': remaining_time,
                    'is_otp_expired': is_otp_expired
                })

        except AdminProfile.DoesNotExist:
            cleanup_pending_registration(request)
            messages.error(request, 'Admin profile not found. Please register again.')
            return redirect('register_administrator')


def verify_student_otp(request):
    """Handle student OTP verification - Step 2: Verify account"""
    if request.method == 'GET':
        # Check if there's a pending student verification
        if 'pending_student_id' not in request.session:
            messages.error(request, 'No pending verification found. Please register first.')
            return redirect('register_student')

        # Calculate remaining time for the current OTP
        remaining_time = 0
        is_otp_expired = False
        try:
            student_profile = StudentProfile.objects.get(user_id=request.session.get('pending_student_id'))
            if student_profile.otp_created_at:
                elapsed_time = (timezone.now() - student_profile.otp_created_at).total_seconds()
                remaining_time = max(0, 600 - int(elapsed_time))
                is_otp_expired = elapsed_time >= 600
        except StudentProfile.DoesNotExist:
            # If student profile doesn't exist, cleanup and redirect
            cleanup_pending_student_registration(request)
            messages.error(request, 'Registration session expired. Please register again.')
            return redirect('register_student')

        return render(request, 'verify_otp.html', {
            'remaining_time': remaining_time,
            'is_otp_expired': is_otp_expired
        })

    elif request.method == 'POST':
        # Verify OTP code
        entered_otp = request.POST.get('otp_code')
        pending_student_id = request.session.get('pending_student_id')

        if not entered_otp:
            messages.error(request, 'Please enter the verification code.')
            # Calculate remaining time for error case
            remaining_time = 0
            is_otp_expired = False
            try:
                student_profile = StudentProfile.objects.get(user_id=pending_student_id)
                if student_profile.otp_created_at:
                    elapsed_time = (timezone.now() - student_profile.otp_created_at).total_seconds()
                    remaining_time = max(0, 600 - int(elapsed_time))
                    is_otp_expired = elapsed_time >= 600
            except StudentProfile.DoesNotExist:
                cleanup_pending_student_registration(request)
                messages.error(request, 'Registration session expired. Please register again.')
                return redirect('register_student')
            return render(request, 'verify_otp.html', {
                'remaining_time': remaining_time,
                'is_otp_expired': is_otp_expired
            })

        if not pending_student_id:
            messages.error(request, 'Session expired. Please register again.')
            return redirect('register_student')

        try:
            student_profile = StudentProfile.objects.get(user_id=pending_student_id)

            # Check if OTP is expired first
            if student_profile.is_otp_expired():
                messages.error(request,
                               'Verification code has expired. Please request a new code using the "Resend Code" link.')
                return render(request, 'verify_otp.html', {
                    'remaining_time': 0,
                    'is_otp_expired': True
                })

            # Then check if OTP is correct
            if student_profile.otp_code == entered_otp:
                # OTP verified successfully
                student_profile.is_verified = True
                student_profile.otp_code = None
                student_profile.otp_created_at = None
                student_profile.save()

                student_profile.user.is_active = True
                student_profile.user.save()

                # Clean up session including resend counter
                request.session.flush()

                messages.success(request, 'Account verified successfully! Please log in to continue.')
                return redirect('login')
            else:
                # OTP is incorrect but still valid (not expired)
                # Calculate remaining time for the current OTP
                elapsed_time = (timezone.now() - student_profile.otp_created_at).total_seconds()
                remaining_time = max(0, 600 - int(elapsed_time))
                is_otp_expired = elapsed_time >= 600

                messages.error(request, 'Invalid verification code. Please try again with the same code.')
                return render(request, 'verify_otp.html', {
                    'remaining_time': remaining_time,
                    'is_otp_expired': is_otp_expired
                })

        except StudentProfile.DoesNotExist:
            cleanup_pending_student_registration(request)
            messages.error(request, 'Student profile not found. Please register again.')
            return redirect('register_student')


def resend_otp(request):
    """Resend OTP verification code - Maximum 3 attempts allowed"""
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
            cleanup_pending_registration(request)
            return redirect('register_administrator')

        # Check OTP resend attempt count
        otp_resend_count = request.session.get('otp_resend_count', 0)

        if otp_resend_count >= 3:
            messages.error(
                request,
                'Maximum OTP resend attempts (3) reached. Please register again.'
            )
            # Clean up this registration
            cleanup_pending_registration(request)
            return redirect('register_administrator')

        # Generate and send new OTP (this creates a new OTP with fresh timestamp)
        email_sent = send_otp_email(admin_profile, request)

        if email_sent:
            # Increment resend counter
            otp_resend_count += 1
            request.session['otp_resend_count'] = otp_resend_count

            attempts_remaining = 3 - otp_resend_count
            messages.success(
                request,
                f'New verification code sent! Please check your email. ({attempts_remaining} attempts remaining)'
            )

            # Force session save to ensure counter is updated
            request.session.modified = True

        else:
            messages.error(request, 'Failed to send verification code. Please try again.')

        # Always redirect back to verify OTP page with resend parameter
        return redirect('verify_otp')

    except AdminProfile.DoesNotExist:
        cleanup_pending_registration(request)
        messages.error(request, 'Admin profile not found. Please register again.')
        return redirect('register_administrator')


def resend_student_otp(request):
    """Resend OTP verification code for students - Maximum 3 attempts allowed"""
    pending_student_id = request.session.get('pending_student_id')

    if not pending_student_id:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register_student')

    try:
        student_profile = StudentProfile.objects.get(user_id=pending_student_id)

        if student_profile.is_verified:
            messages.info(request, 'Your account is already verified.')
            return redirect('student_dashboard')

        # Check OTP resend attempt count
        otp_resend_count = request.session.get('student_otp_resend_count', 0)

        if otp_resend_count >= 3:
            messages.error(
                request,
                'Maximum OTP resend attempts (3) reached. Please register again.'
            )
            # Clean up this registration
            cleanup_pending_student_registration(request)
            return redirect('register_student')

        # Generate and send new OTP (this creates a new OTP with fresh timestamp)
        email_sent = send_student_otp_email(student_profile, request)

        if email_sent:
            # Increment resend counter
            otp_resend_count += 1
            request.session['student_otp_resend_count'] = otp_resend_count

            attempts_remaining = 3 - otp_resend_count
            messages.success(
                request,
                f'New verification code sent! Please check your email. ({attempts_remaining} attempts remaining)'
            )

            # Force session save to ensure counter is updated
            request.session.modified = True

        else:
            messages.error(request, 'Failed to send verification code. Please try again.')

        # Always redirect back to verify OTP page with resend parameter
        return redirect('verify_student_otp')

    except StudentProfile.DoesNotExist:
        cleanup_pending_student_registration(request)
        messages.error(request, 'Student profile not found. Please register again.')
        return redirect('register_student')