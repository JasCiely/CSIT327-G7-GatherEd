from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
# Import the Event model (adjust the path if needed)
from apps.admin_dashboard_page.models import Event


# Assuming your Event model is located in 'apps.admin_dashboard_page.models'

@login_required
def manage_feedback(request):
    """
    Manages and reviews event feedback, filtering events by the logged-in user.
    """
    is_ajax = request.GET.get('is_ajax') == 'true'

    # Filter Events by Logged-in Admin
    try:
        # Filter events where the event's 'admin' (AdminProfile) is linked to the current 'request.user'
        events_query = Event.objects.filter(
            admin__user=request.user
        ).order_by('date', 'start_time')
    except Exception:
        events_query = Event.objects.none()

    # Placeholder Data

    template_context = {
        'title': 'Manage Feedback',

        # Pass the filtered events list to the template
        'events_list': events_query,

        # Placeholder statistics (as requested)
        'avg_rating': "N/A",
        'total_submissions': "0",
        'new_feedback': "0",
        # --- KEY CHANGE HERE: Placeholder for Events Reviewed ---
        'events_reviewed': "N/A",

        # Empty list for the feedback data
        'feedback_list': [],
    }

    if request.method == 'POST':
        # Placeholder POST logic
        return redirect('manage_feedback')
    else:
        template_name = 'fragments/manage_feedback/manage_feedback_content.html'

        if not is_ajax:
            return redirect('admin_dashboard')

        return render(request, template_name, template_context)