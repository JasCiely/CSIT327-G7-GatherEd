from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def student_dashboard(request):
    is_ajax = request.GET.get('is_ajax') == 'true'

    template_context = {
        'upcoming_events_count': 0,
        'total_registered_count': 0,
        'events_attended_count': 0,
        'next_event': None,
    }

    if is_ajax:
        return render(request, 'fragments/dashboard_content.html', template_context)
    else:
        return render(request, 'student_dashboard.html', template_context)