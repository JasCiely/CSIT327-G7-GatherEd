from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client, Client
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from datetime import datetime

def register(request):
    # --- 0. CRITICAL FIX: INITIALIZE SUPABASE CLIENTS ---
    global user
    try:
        # The public client is used for read-only checks (like checking if an ID exists)
        # Assuming you have SUPABASE_ANON_KEY defined in settings
        supabase_public: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        # The admin client is used for privileged writes (user creation)
        supabase_admin: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    except AttributeError:
        # Handle case where keys are not set in settings
        messages.error(request, "Server configuration error: Supabase keys are missing.")
        # CORRECTED PATH: 'users/register.html'
        return render(request, 'register.html')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        name = request.POST.get('name')
        user_type = request.POST.get('user_type')
        cit_id = request.POST.get('cit_id')

        # --- VALIDATION (Simplified & Cleaned) ---
        if not all([email, password, cit_id, name, user_type]):
            messages.error(request, 'All fields are required.')
            # CORRECTED PATH: 'users/register.html'
            return render(request, 'register.html')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            # CORRECTED PATH: 'users/register.html'
            return render(request, 'register.html')

        if not email.endswith('@cit.edu'):
            messages.error(request, 'Registration is limited to @cit.edu email addresses only.')
            # CORRECTED PATH: 'users/register.html'
            return render(request, 'register.html')

        cleaned_cit_id = cit_id.replace('-', '')
        if not cleaned_cit_id.isdigit() or len(cleaned_cit_id) != 9:
            messages.error(request, 'The ID must be exactly 9 digits long.')
            # CORRECTED PATH: 'users/register.html'
            return render(request, 'register.html')
        formatted_cit_id = f"{cleaned_cit_id[:2]}-{cleaned_cit_id[2:6]}-{cleaned_cit_id[6:]}"

        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
            # CORRECTED PATH: 'users/register.html'
            return render(request, 'register.html')

        # --- CIT ID EXISTENCE CHECK (Using the correct table names from migration) ---
        # Note: We must use the table names defined in models.py (admins, students)
        # Assuming your Supabase tables are named 'admins' and 'students' from the last successful migration.
        student_id_check = supabase_public.table('students').select('cit_id').eq('cit_id', formatted_cit_id).execute().data
        admin_id_check = supabase_public.table('admins').select('cit_id').eq('cit_id', formatted_cit_id).execute().data

        if student_id_check or admin_id_check:
            messages.error(request, 'This ID is already registered.')
            # CORRECTED PATH: 'users/register.html'
            return render(request, 'register.html')

        # --- ACCOUNT CREATION: AUTOMATIC ROLE-BASED PERMISSION ---
        try:
            # Determine if the user should be a staff member (for Django Admin access)
            is_staff_user = (user_type == 'administrator')

            # 1. Create the Django user, applying the is_staff permission
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                is_staff=is_staff_user
            )

            # 2. Create profile in Supabase
            if user_type == 'administrator':
                # Use the 'admins' table as defined in your models.py
                admin_result = supabase_admin.table('admins').insert({
                    # Django FK column name is '<ModelName>_id', but your SQL requested 'user_id'
                    # We use 'user_id' because Django ORM handles the field name mapping.
                    'user_id': str(user.pk),
                    'name': name,
                    'cit_id': formatted_cit_id,
                    'created_at': datetime.now().isoformat()
                }).execute()
                if not admin_result.data:
                    user.delete()
                    raise Exception("Failed to insert admin profile into admins table.")
                redirect_path = 'admin_dashboard'

            elif user_type == 'student':
                # Use the 'students' table as defined in your models.py
                student_result = supabase_admin.table('students').insert({
                    'user_id': str(user.pk),
                    'name': name,
                    'cit_id': formatted_cit_id,
                    'created_at': datetime.now().isoformat()
                }).execute()
                if not student_result.data:
                    user.delete()
                    raise Exception("Failed to insert student profile into students table.")
                redirect_path = 'student_dashboard'

            else:
                user.delete()
                raise Exception("Invalid user type.")

            # 3. Log the user in immediately (Unchanged)
            logged_in_user = authenticate(request, username=email, password=password)
            if logged_in_user is not None:
                login(request, logged_in_user)
                messages.success(request, 'Registration successful! You are now logged in.')
                return redirect(redirect_path)
            else:
                messages.warning(request,
                                 'Registration successful, but automatic login failed. Please log in manually.')
                return redirect('login')

        except Exception as e:
            # Final cleanup check for the Django User object
            if 'user' in locals():
                try:
                    user.delete()
                except:
                    pass

            messages.error(request, f'Registration failed: {str(e)}')
            # CORRECTED PATH: 'users/register.html'
            return render(request, 'register.html')

    # CORRECTED PATH: 'users/register.html'
    return render(request, 'register.html')