from django.shortcuts import render, redirect
from django.db.models import Count, Case, When, BooleanField, Value, Q
from datetime import date, datetime

from apps.admin_dashboard_page.models import Event
from apps.register_page.models import StudentProfile


def event_list(request):
    """
    Displays upcoming and active events for the student dashboard.
    - Completed events are hidden.
    - Ongoing events show as 'Ongoing'.
    - Future events can be 'Available', 'Full', 'Registered', or 'Registration Closed'.
    """

    # --- 1. Identify logged-in student ---
    current_student = None
    if request.user.is_authenticated:
        try:
            current_student = StudentProfile.objects.get(user=request.user)
        except StudentProfile.DoesNotExist:
            current_student = None

    today = date.today()
    now = datetime.now().time()

    # --- 2. Filter out completed events ---
    upcoming_and_active_events = (
        Event.objects
        .filter(
            Q(date__gt=today) | Q(date=today, end_time__gte=now)
        )
        .select_related('admin')
        .annotate(
            registered_count=Count('registrations', filter=Q(registrations__status__in=['REGISTERED', 'ATTENDED']))
        )
        .annotate(
            is_registered_by_student=Case(
                When(
                    registrations__student=current_student,
                    registrations__status='REGISTERED',
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            )
        )
        .order_by('date', 'start_time')
    )

    # --- 3. Build event list with proper statuses ---
    events_list = []
    for event in upcoming_and_active_events:
        is_full = (
            event.max_attendees is not None
            and event.max_attendees > 0
            and event.registered_count >= event.max_attendees
        )

        # Determine if the event is happening today
        is_today = event.date == today

        # Default: assume registration is open unless logic says otherwise
        registration_open = getattr(event, 'is_registration_open', True)

        # Determine status
        if event.is_registered_by_student:
            status = 'Registered'
        elif is_today:
            status = 'Closed – Event Ongoing'  # 🕒 The event is happening now
        elif is_full:
            status = 'Full'
        elif not registration_open:
            status = 'Registration Closed'
        else:
            status = 'Available'

        events_list.append({
            'id': event.id,
            'name': event.title,
            'date': event.date.strftime('%b %d, %Y'),
            'time': f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}",
            'organization': event.admin.organization_name,
            'location': event.location or 'N/A',
            'status': status,
        })

    context = {'events_list': events_list}

    # --- 4. Handle AJAX vs normal refresh ---
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.GET.get('is_ajax') == 'true'
    )

    if is_ajax:
        # ✅ Return fragment for in-dashboard navigation / refresh
        return render(request, 'fragments/event_list/event_list_content.html', context)
    else:
        # 🚀 Redirect back to main dashboard on manual page reload
        return redirect('student_dashboard')
