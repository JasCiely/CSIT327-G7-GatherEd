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

        if not all([email, password, confirm_password, name, user_type, cit_id]):
            messages.error(request, 'All fields are required.')
            return render(request, 'register.html')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html')

        # --- Password Validation ---
        if not re.fullmatch(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$', password):
            messages.error(
                request,
                'Password must be at least 8 characters long and contain an uppercase, lowercase, and number.'
            )
            return render(request, 'register.html')

        if not email.endswith('@cit.edu'):
            messages.error(request, 'Only @cit.edu email addresses are allowed.')
            return render(request, 'register.html')

        # --- Strict CIT ID Format ---
        if not re.fullmatch(r'\d{2}-\d{4}-\d{3}', cit_id):
            messages.error(request, 'CIT ID must follow this format: XX-XXXX-XXX (e.g., 12-3456-789).')
            return render(request, 'register.html')

        formatted_cit_id = cit_id.strip()

        if User.objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered.')
            return render(request, 'register.html')

        student_id_check = supabase_public.table('students').select('cit_id').eq('cit_id', formatted_cit_id).execute().data
        admin_id_check = supabase_public.table('admins').select('cit_id').eq('cit_id', formatted_cit_id).execute().data

        if student_id_check or admin_id_check:
            messages.error(request, 'This CIT ID is already registered.')
            return render(request, 'register.html')

        try:
            is_staff_user = (user_type == 'administrator')

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                is_staff=is_staff_user
            )

            table_name = 'admins' if user_type == 'administrator' else 'students'
            result = supabase_admin.table(table_name).insert({
                'user_id': str(user.pk),
                'name': name,
                'cit_id': formatted_cit_id,
                'created_at': datetime.now().isoformat()
            }).execute()

            if not result.data:
                user.delete()
                raise Exception(f"Failed to insert {user_type} profile.")

            logged_in_user = authenticate(request, username=email, password=password)
            if logged_in_user:
                login(request, logged_in_user)
                messages.success(request, 'Registration successful! Redirecting to your dashboard...')
                return redirect('admin_dashboard' if user_type == 'administrator' else 'student_dashboard')
            else:
                messages.warning(request, 'Registration successful, but login failed. Please log in manually.')
                return redirect('login_view')

        except Exception as e:
            if 'user' in locals():
                try:
                    user.delete()
                except:
                    pass
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'register.html')

    return render(request, 'register.html')
