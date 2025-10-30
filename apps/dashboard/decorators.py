# apps/dashboard/decorators.py

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from functools import wraps

def login_and_no_cache(view_func):
    """Requires login and prevents caching so logged-out users can't go back."""
    @login_required(login_url='login')
    @never_cache
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    return wrapped_view
