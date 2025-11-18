from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from apps.register_page.models import AdminProfile, StudentProfile

USER_ROLE_SESSION_KEY = 'user_role'

def login_view(request):
    if request.method != 'POST':
        return render(request, 'login.html')

    email = request.POST.get('email')
    password = request.POST.get('password')

    if not email or not password:
        messages.error(request, 'Email and password are required.')
        return redirect('login')

    user = authenticate(request, username=email, password=password)
    if not user:
        messages.error(request, "Invalid credentials. Please try again.")
        return redirect('login')

    login(request, user)

    cached_role = request.session.get(USER_ROLE_SESSION_KEY)
    if cached_role:
        return redirect(f'{cached_role}_dashboard')

    user_role = None
    if AdminProfile.objects.filter(user=user).exists():
        user_role = 'admin'
    elif StudentProfile.objects.filter(user=user).exists():
        user_role = 'student'

    if user_role:
        request.session[USER_ROLE_SESSION_KEY] = user_role
        return redirect(f'{user_role}_dashboard')

    logout(request)
    messages.error(request, "No role assigned to this user. Contact support.")
    return redirect('login')


def logout_view(request):
    request.session.pop(USER_ROLE_SESSION_KEY, None)
    logout(request)

    response = redirect('index')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
