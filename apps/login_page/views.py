from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client, Client
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User

# Constant for session key
USER_ROLE_SESSION_KEY = 'user_role'


def get_supabase_client():
    """Helper to create or get the Supabase client, handling potential configuration errors."""
    try:
        return create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
    except AttributeError:
        # Re-raise or handle this error at the call site
        raise EnvironmentError("Server configuration error: Supabase keys are missing.")


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'login.html')

        # 1. Critical Django Authentication (FASTEST PATH)
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # 2. Log in the user immediately
            login(request, user)

            # --- New Optimization: Check Session Cache First! ---
            user_role = request.session.get(USER_ROLE_SESSION_KEY)

            if user_role == 'admin':
                return redirect('admin_dashboard')
            elif user_role == 'student':
                return redirect('student_dashboard')

            # --- If role is NOT in session, proceed to check Supabase (Slow Path) ---
            try:
                supabase_public: Client = get_supabase_client()
            except EnvironmentError as e:
                logout(request)
                messages.error(request, str(e))
                return render(request, 'login.html')

            user_pk_str = str(user.pk)

            try:
                # Check for Admin role
                admin_check = supabase_public.table('admins') \
                    .select('user_id') \
                    .eq('user_id', user_pk_str) \
                    .limit(1).execute().data

                if admin_check:
                    # --- CRITICAL NEW STEP: Cache the role ---
                    request.session[USER_ROLE_SESSION_KEY] = 'admin'
                    return redirect('admin_dashboard')

                # Check for Student role
                student_check = supabase_public.table('students') \
                    .select('user_id') \
                    .eq('user_id', user_pk_str) \
                    .limit(1).execute().data

                if student_check:
                    # --- CRITICAL NEW STEP: Cache the role ---
                    request.session[USER_ROLE_SESSION_KEY] = 'student'
                    return redirect('student_dashboard')

                # No profile found
                messages.error(request, "User profile not found. Contact support.")
                logout(request)
                return render(request, 'login.html')

            except Exception as e:
                # External service failure
                logout(request)
                messages.error(request, f"Error checking user profile: {e}. Please try again.")
                return render(request, 'login.html')

        else:
            # Authentication Failed
            messages.error(request, "Invalid credentials. If you're not registered, please sign up.")
            return render(request, 'login.html')

    return render(request, 'login.html')


def logout_view(request):
    # Explicitly remove the cached role
    if USER_ROLE_SESSION_KEY in request.session:
        del request.session[USER_ROLE_SESSION_KEY]

    logout(request)
    # request.session.flush() is an alternative, but explicitly deleting the key is cleaner
    # if you want other non-security-critical session data to persist.

    messages.success(request, "You have been logged out.")
    return redirect('index')