from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import render, redirect

from apps.login_page.views import USER_ROLE_SESSION_KEY

def index_view(request):
    return render(request, 'index.html')

def logout_view(request):

    request.session.pop(USER_ROLE_SESSION_KEY, None)

    logout(request)

    referer = request.META.get('HTTP_REFERER', '')
    if 'dashboard' in referer:
        messages.success(request, "You have been successfully logged out.")

    return redirect('index')
