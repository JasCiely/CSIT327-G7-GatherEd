from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.admin_dashboard_page.models import Event

@login_required
def track_attendance(request):
    is_ajax = request.GET.get('is_ajax') == 'true'

    try:
        events_query = Event.objects.filter(
            admin__user=request.user
        ).order_by('date', 'start_time')
    except Exception:
        events_query = Event.objects.none()

    template_context = {
        'events_list': events_query,
        'title': 'Track Attendance'
    }

    if request.method == 'POST':
        return redirect('track_attendance')
    else:
        template_name = 'fragments/track_attendance/track_attendance_content.html'

        if not is_ajax:
            return redirect('admin_dashboard')

        return render(request, template_name, template_context)
