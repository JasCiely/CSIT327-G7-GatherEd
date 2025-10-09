from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client, Client
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User



def login_view(request):
    try:
        supabase_public: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
    except AttributeError:
        messages.error(request, "Server configuration error: Supabase keys are missing.")
        return render(request, 'login.html')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'login.html')

        try:
            User.objects.get(username=email)
        except User.DoesNotExist:
            messages.error(request, "Account not registered")
            return render(request, 'login.html')

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            try:
                admin_check = supabase_public.table('admins').select('user_id').eq('user_id', str(user.pk)).limit(1).execute().data
                if admin_check:
                    return redirect('admin_dashboard')

                student_check = supabase_public.table('students').select('user_id').eq('user_id', str(user.pk)).limit(1).execute().data
                if student_check:
                    return redirect('student_dashboard')

                messages.error(request, "User profile not found. Contact support.")
                return render(request, 'login.html')

            except Exception as e:
                messages.error(request, f"Error checking user profile: {e}")
                return render(request, 'login.html')

        else:
            messages.error(request, "Invalid credentials")
            return render(request, 'login.html')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    request.session.flush()
    messages.success(request, "You have been logged out.")
    # Assuming 'index' is the correct URL name for the homepage
    return redirect('index')