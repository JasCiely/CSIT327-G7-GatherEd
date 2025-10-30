from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client, Client
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout

USER_ROLE_SESSION_KEY = 'user_role'
_supabase_client = None


def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client:
        return _supabase_client
    _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _supabase_client


def _check_user_role_fast(supabase_client: Client, user_pk: str) -> str | None:
    if supabase_client.table('admins').select('user_id').eq('user_id', user_pk).limit(1).execute().data:
        return 'admin'
    if supabase_client.table('students').select('user_id').eq('user_id', user_pk).limit(1).execute().data:
        return 'student'
    return None


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

    supabase_client = get_supabase_client()
    user_role = _check_user_role_fast(supabase_client, str(user.pk))
    if user_role:
        request.session[USER_ROLE_SESSION_KEY] = user_role
        return redirect(f'{user_role}_dashboard')

    logout(request)
    return redirect('login')


def logout_view(request):
    """
    Logs out the user and prevents back-button from showing previous pages.
    """
    request.session.pop(USER_ROLE_SESSION_KEY, None)
    logout(request)

    response = redirect('index')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
