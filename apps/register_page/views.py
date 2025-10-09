from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from supabase import create_client, Client
from datetime import datetime
import re

def register(request):
    try:
        supabase_public: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        supabase_admin: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    except AttributeError:
        messages.error(request, "Server configuration error: Supabase keys are missing.")
        return render(request, 'register.html')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        name = request.POST.get('name')
        user_type = request.POST.get('user_type')
        cit_id = request.POST.get('cit_id')

        # 1. EXTRACT NEW FIELD
        organization_name = request.POST.get('organization_name')

        # --- BASIC FIELD VALIDATION ---
        # Note: organization_name is intentionally excluded here as it's conditional
        if not all([email, password, cit_id, name, user_type]):
            messages.error(request, 'All required form fields are missing. Please fill out the form completely.')
            return render(request, 'register.html')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html')

        # --- USER TYPE SPECIFIC VALIDATION: ADMINISTRATOR ---
        if user_type == 'administrator':
            # 2. VALIDATION: Organization is required for administrators
            if not organization_name:
                messages.error(request, 'Administrator registration requires selecting an Organization Affiliation.')
                return render(request, 'register.html')

        # --- PASSWORD VALIDATION ---
        if not (
                len(password) >= 8 and
                re.search(r'[A-Z]', password) and
                re.search(r'[a-z]', password) and
                re.search(r'\d', password)
        ):
            messages.error(
                request,
                'Your password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number.'
            )
            return render(request, 'register.html')

        if not email.endswith('@cit.edu'):
            messages.error(request, 'Registration is limited to @cit.edu email addresses only.')
            return render(request, 'register.html')

        # --- STRICT ID VALIDATION: must be XX-XXXX-XXX ---
        if not re.fullmatch(r'\d{2}-\d{4}-\d{3}', cit_id):
            messages.error(request, 'CIT ID must follow the format: XX-XXXX-XXX (e.g., 12-3456-789).')
            return render(request, 'register.html')

        formatted_cit_id = cit_id

        # --- PRE-REGISTRATION CHECKS ---

        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
            return render(request, 'register.html')

        # Check if CIT ID is already registered in either table
        student_id_check = supabase_public.table('students').select('cit_id').eq('cit_id',
                                                                                 formatted_cit_id).execute().data
        admin_id_check = supabase_public.table('admins').select('cit_id').eq('cit_id', formatted_cit_id).execute().data

        if student_id_check or admin_id_check:
            messages.error(request, 'This ID is already registered.')
            return render(request, 'register.html')

        # 3. ORGANIZATION UNIQUENESS CHECK (NEW LOGIC)
        if user_type == 'administrator':
            try:
                # Check if any admin already exists with this organization name
                org_check = supabase_public.table('admins') \
                    .select('organization_name') \
                    .eq('organization_name', organization_name) \
                    .execute().data

                if org_check:
                    messages.error(request,
                                   f'Registration failed: The organization "{organization_name}" already has an assigned administrator.')
                    return render(request, 'register.html')
            except Exception as e:
                messages.error(request, f'A database error occurred during organization check: {str(e)}')
                return render(request, 'register.html')

        # --- REGISTRATION PROCESS ---
        try:
            is_staff_user = (user_type == 'administrator')

            # 1. Create Django User
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                is_staff=is_staff_user
            )

            # 2. Insert Profile Data into Supabase
            if user_type == 'administrator':
                insert_data = {
                    'user_id': str(user.pk),
                    'name': name,
                    'cit_id': formatted_cit_id,
                    # INCLUDE ORGANIZATION_NAME IN THE INSERT
                    'organization_name': organization_name,
                    'created_at': datetime.now().isoformat()
                }
                result = supabase_admin.table('admins').insert(insert_data).execute()

                if not result.data:
                    user.delete()
                    raise Exception("Failed to insert admin profile into Supabase.")
                redirect_path = 'admin_dashboard'

            elif user_type == 'student':
                insert_data = {
                    'user_id': str(user.pk),
                    'name': name,
                    'cit_id': formatted_cit_id,
                    'created_at': datetime.now().isoformat()
                }
                result = supabase_admin.table('students').insert(insert_data).execute()

                if not result.data:
                    user.delete()
                    raise Exception("Failed to insert student profile into Supabase.")
                redirect_path = 'student_dashboard'

            else:
                user.delete()
                raise Exception("Invalid user type.")

            # 3. Log User In
            logged_in_user = authenticate(request, username=email, password=password)
            if logged_in_user:
                login(request, logged_in_user)
                messages.success(request, 'Registration successful! You are now logged in.')
                # Assuming 'admin_dashboard' and 'student_dashboard' are defined in urls.py
                return redirect(redirect_path)
            else:
                messages.warning(request,
                                 'Registration successful, but automatic login failed. Please log in manually.')
                return redirect('login_view')

        except Exception as e:
            # Clean up Django User if Supabase insert fails
            if 'user' in locals():
                try:
                    user.delete()
                except:
                    pass
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'register.html')

    return render(request, 'register.html')