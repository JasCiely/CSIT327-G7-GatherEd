# apps/login_page/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
import logging
import traceback
from django.contrib.auth import login, authenticate, logout
from apps.register_page.models import AdminProfile, StudentProfile

USER_ROLE_SESSION_KEY = 'user_role'
logger = logging.getLogger(__name__)

def login_view(request):
    if request.method != 'POST':
        return render(request, 'login.html')

    try:
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return redirect('login')

        logger.info(f"Attempting login for email: {email}")

        user = authenticate(request, username=email, password=password)
        if not user:
            messages.error(request, "Invalid credentials. Please try again.")
            return redirect('login')

        logger.info(f"User authenticated: {user.username}, is_staff: {user.is_staff}")

        # Check if user is an admin and verify their status
        try:
            admin_profile = AdminProfile.objects.get(user=user)
            logger.info(f"Admin profile found: {admin_profile.name}, verified: {admin_profile.is_verified}")
            if not admin_profile.is_verified:
                messages.error(request, "Please verify your email address before logging in. Check your email for the verification code.")
                return redirect('login')
        except AdminProfile.DoesNotExist:
            logger.info("No admin profile found, assuming student")
            # User is not an admin, continue with student login
            pass

        login(request, user)
        logger.info("User logged in successfully")

        cached_role = request.session.get(USER_ROLE_SESSION_KEY)
        if cached_role:
            logger.info(f"Using cached role: {cached_role}")
            return redirect(f'{cached_role}_dashboard')

        user_role = None
        try:
            if AdminProfile.objects.filter(user=user).exists():
                user_role = 'admin'
                logger.info("User role determined as: admin")
            elif StudentProfile.objects.filter(user=user).exists():
                user_role = 'student'
                logger.info("User role determined as: student")
        except Exception as e:
            logger.error(f"Error determining user role: {str(e)}")
            logout(request)
            messages.error(request, "Error determining user role. Please try again.")
            return redirect('login')

        if user_role:
            request.session[USER_ROLE_SESSION_KEY] = user_role
            logger.info(f"Redirecting to: {user_role}_dashboard")
            return redirect(f'{user_role}_dashboard')

        logout(request)
        messages.error(request, "No role assigned to this user. Contact support.")
        return redirect('login')

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(request, "An unexpected error occurred during login. Please try again.")
        return redirect('login')

def logout_view(request):
    request.session.pop(USER_ROLE_SESSION_KEY, None)
    logout(request)

    response = redirect('index')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response