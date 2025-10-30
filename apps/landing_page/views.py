# apps/landing_page/views.py

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from apps.login_page.views import USER_ROLE_SESSION_KEY

@never_cache
def index_view(request):
    return render(request, 'index.html')


@never_cache
def logout_view(request):
    """
    Logs out the user and redirects to the index page.
    """
    logout(request)
    messages.success(request, "You have successfully logged out.")

    # Redirect to index
    response = redirect('index')

    # Prevent caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response