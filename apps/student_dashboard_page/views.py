from datetime import datetime, time as time_obj
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from apps.register_page.models import StudentProfile
from .models import Registration


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    response = redirect('index')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def student_dashboard(request):
    is_ajax = request.GET.get('is_ajax') == 'true'

    try:
        student_profile = StudentProfile.objects.get(user=request.user)
        user_display_name = student_profile.name
    except StudentProfile.DoesNotExist:
        user_display_name = request.user.email or "Student"

    # Count events (unchanged)
    total_registered_events = Registration.objects.filter(
        student=student_profile,
        status='REGISTERED'
    ).count()

    total_attendance_recorded = Registration.objects.filter(
        student=student_profile,
        status='ATTENDED'
    ).count()

    total_cancel_events = Registration.objects.filter(
        student=student_profile,
        status='CANCELLED'
    ).count()

    # Get current date and time (timezone-aware)
    now = timezone.now()

    # 1. Filter all relevant registered events.
    #    The 'REGISTERED' status automatically excludes 'CANCELLED' events.
    registered_events = Registration.objects.filter(
        student=student_profile,
        status='REGISTERED',
    ).select_related('event').order_by('event__date', 'event__start_time')

    # Initialize next event variables
    upcoming_registration = None
    min_delta = None

    # 2. Iterate and find the absolute next event in the future
    for registration in registered_events:
        event = registration.event

        # Use time_obj.min (00:00:00) if start_time is missing
        event_start_time = event.start_time if event.start_time else time_obj.min

        # Create a timezone-aware datetime object for the event
        event_datetime_naive = datetime.combine(event.date, event_start_time)
        event_datetime_aware = timezone.make_aware(event_datetime_naive)

        # Check if this event is in the future
        if event_datetime_aware > now:
            time_difference = event_datetime_aware - now

            # Find the closest event chronologically
            if upcoming_registration is None or time_difference < min_delta:
                upcoming_registration = registration
                min_delta = time_difference

    # 3. Prepare event data for template
    next_event_data = None
    if upcoming_registration:
        next_event_data = {
            'title': upcoming_registration.event.title,
            'date': upcoming_registration.event.date,
            'location': upcoming_registration.event.location,
            'start_time': upcoming_registration.event.start_time,
            'end_time': upcoming_registration.event.end_time,
            'status': upcoming_registration.status,
        }

    template_context = {
        'user_display_name': user_display_name,
        'total_registered_events': total_registered_events,
        'total_attendance_recorded': total_attendance_recorded,
        'total_cancel_events': total_cancel_events,
        'next_event': next_event_data,
    }

    if is_ajax:
        return render(request, 'fragments/dashboard_content_student.html', template_context)

    return render(request, 'student_dashboard.html', template_context)