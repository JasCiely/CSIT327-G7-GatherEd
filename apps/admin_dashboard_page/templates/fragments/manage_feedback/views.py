from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.admin_dashboard_page.models import Event


@login_required
def manage_feedback(request):
    is_ajax = request.GET.get('is_ajax') == 'true'

    try:
        events_query = Event.objects.filter(
            admin__user=request.user
        ).order_by('date', 'start_time')
    except Exception:
        events_query = Event.objects.none()

    template_context = {
        'title': 'Manage Feedback',
        'events_list': events_query,
        'avg_rating': "N/A",
        'total_submissions': "0",
        'new_feedback': "0",
        'events_reviewed': "N/A",
        'feedback_list': [],
    }

    if request.method == 'POST':
        return redirect('manage_feedback')
    else:
        template_name = 'fragments/manage_feedback/manage_feedback_content.html'

        if not is_ajax:
            return redirect('admin_dashboard')

        return render(request, template_name, template_context)
