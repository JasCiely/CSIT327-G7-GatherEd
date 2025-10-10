from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from supabase import create_client, Client
from datetime import datetime
import re
from postgrest.exceptions import APIError

# Constants for validation regex
CIT_ID_REGEX = r'^\d{2}-\d{4}-\d{3}$'
EMAIL_DOMAIN = '@cit.edu'


def get_supabase_clients(request):
    """Helper to create or get the Supabase clients, handling potential configuration errors."""
    try:
        # Avoid creating clients if keys are missing
        if not all([settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY, settings.SUPABASE_SERVICE_ROLE_KEY]):
            raise AttributeError("Missing Supabase configuration keys.")

        supabase_public: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        supabase_admin: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        return supabase_public, supabase_admin
    except AttributeError:
        messages.error(request, "Server configuration error: Supabase keys are missing.")
        raise EnvironmentError("Supabase keys are missing.")


def register(request):
    if request.method != 'POST':
        return render(request, 'register.html')

    # --- Data Extraction ---
    email = request.POST.get('email')
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')
    name = request.POST.get('name')
    user_type = request.POST.get('user_type')
    cit_id = request.POST.get('cit_id')
    organization_name = request.POST.get('organization_name')
    formatted_cit_id = cit_id

    # --- 1. Max-Speed Field/Syntax Validation ---
    if not all([email, password, cit_id, name, user_type]):
        messages.error(request, 'Please fill out all required fields.')
        return render(request, 'register.html')
    if password != confirm_password:
        messages.error(request, 'Passwords do not match.')
        return render(request, 'register.html')
    if user_type == 'administrator' and not organization_name:
        messages.error(request, 'Administrator registration requires an Organization Affiliation.')
        return render(request, 'register.html')
    if not (len(password) >= 8 and re.search(r'[A-Z]', password) and re.search(r'[a-z]', password) and re.search(r'\d',
                                                                                                                 password)):
        messages.error(request, 'Password must meet complexity requirements.')
        return render(request, 'register.html')
    if not email.endswith(EMAIL_DOMAIN):
        messages.error(request, f'Registration is limited to {EMAIL_DOMAIN} email addresses only.')
        return render(request, 'register.html')
    if not re.fullmatch(CIT_ID_REGEX, cit_id):
        messages.error(request, 'CIT ID must follow the format: XX-XXXX-XXX.')
        return render(request, 'register.html')

    # --- Optimization: Initialize clients here, after fast local checks ---
    try:
        supabase_public, supabase_admin = get_supabase_clients(request)
    except EnvironmentError:
        return render(request, 'register.html')

    # --- 2. Combined Supabase Uniqueness Check (Single-block Network Latency) ---
    try:
        # A. Check if CIT ID is already registered in either table
        # These two API calls (one for students, one for admins) are the necessary bottleneck.
        student_id_check = supabase_public.table('students').select('cit_id').eq('cit_id', formatted_cit_id).limit(
            1).execute().data
        admin_id_check = supabase_public.table('admins').select('cit_id').eq('cit_id', formatted_cit_id).limit(
            1).execute().data

        if student_id_check or admin_id_check:
            messages.error(request, 'This ID is already registered.')
            return render(request, 'register.html')

        # B. Organization Uniqueness Check
        if user_type == 'administrator':
            org_check = supabase_public.table('admins').select('organization_name').eq('organization_name',
                                                                                       organization_name).limit(
                1).execute().data
            if org_check:
                messages.error(request,
                               f'The organization "{organization_name}" already has an assigned administrator.')
                return render(request, 'register.html')

    except APIError as e:
        messages.error(request, f'A database communication error occurred: {e.message}')
        return render(request, 'register.html')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred during checks: {str(e)}')
        return render(request, 'register.html')

    # --- 3. Registration and Profile Insertion (Critical Path) ---
    user = None
    try:
        is_staff_user = (user_type == 'administrator')

        # 1. Create Django User
        # We rely on Django's integrity check to flag duplicate emails now, saving one EXISTS lookup.
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_staff=is_staff_user
        )

        # 2. Insert Profile Data into Supabase
        current_time = datetime.now().isoformat()
        user_pk_str = str(user.pk)

        if user_type == 'administrator':
            insert_data = {
                'user_id': user_pk_str,
                'name': name,
                'cit_id': formatted_cit_id,
                'organization_name': organization_name,
                'created_at': current_time
            }
            # This is the second major blocking call (DB write)
            supabase_admin.table('admins').insert(insert_data).execute()
            redirect_path = 'admin_dashboard'

        else:  # student
            insert_data = {
                'user_id': user_pk_str,
                'name': name,
                'cit_id': formatted_cit_id,
                'created_at': current_time
            }
            supabase_admin.table('students').insert(insert_data).execute()
            redirect_path = 'student_dashboard'

        # 3. Log User In (Very fast internal Django process)
        logged_in_user = authenticate(request, username=email, password=password)
        login(request, logged_in_user)

        messages.success(request, 'Registration successful! You are now logged in.')
        return redirect(redirect_path)

    except Exception as e:
        # Handle duplicate email from create_user and clean up failed Supabase inserts
        if 'IntegrityError' in str(e) or 'duplicate key value' in str(e):
            messages.error(request, 'A user with this email already exists.')
        else:
            messages.error(request, f'Registration failed: {str(e)}')

        # Clean up Django User if a failure occurred after creation
        if user:
            try:
                user.delete()
            except Exception as cleanup_e:
                print(f"Cleanup failed for user {email}: {cleanup_e}")

        return render(request, 'register.html')