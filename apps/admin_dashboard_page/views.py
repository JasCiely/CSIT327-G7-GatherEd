from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def logout_view(request):
    logout(request)
    request.session.flush()
    messages.success(request, "You have been logged out.")
    # Assuming 'index' is the correct URL name for the homepage
    return redirect('index')

@login_required
def admin_dashboard(request):
    """
    Renders the admin dashboard. Returns the full shell or just a fragment based on the request type.
    """

    # --- 1. DETECT REQUEST TYPE ---
    is_ajax = request.GET.get('is_ajax') == 'true'

    # --- 2. GATHER CONTEXT DATA ---
    context = {}

    try:
        # ⚠️ NOTE: Replace these placeholders with your actual Supabase queries.
        total_events = 0
        total_attendance = 0
        new_feedback = 0
        notification_count = 0

        context = {
            'total_events': total_events,
            'total_attendance': total_attendance,
            'new_feedback': new_feedback,
            'notification_count': notification_count,
            'events': [],
        }

    except Exception as e:
        print(f"ERROR: Admin dashboard data fetch failed: {e}")
        pass

    # --- 3. RENDER TEMPLATE BASED ON REQUEST TYPE ---
    if is_ajax:
        # Template Path: admin_portal/fragments/dashboard_content.html
        return render(request, 'fragments/dashboard_content.html', context)
    else:
        # Template Path: admin_portal/admin_dashboard.html
        return render(request, 'admin_dashboard.html', context)