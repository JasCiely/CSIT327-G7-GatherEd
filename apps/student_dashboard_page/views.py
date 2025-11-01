from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from apps.register_page.models import StudentProfile


# NOTE: In a real implementation, you would import Event, Registration, and Feedback models here.
# from your_app.models import Event, Registration, Feedback
# from django.db.models import Count, Max


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

    # --- PLACEHOLDER LOGIC STARTS HERE ---

    # 1. Logic to calculate Total Events Attended (Count where attendance is confirmed)
    # Placeholder: Replace 0 with a query like: Registration.objects.filter(student=student_profile, attended=True).count()
    events_attended = 0

    # 2. Logic to calculate Total Attendance Recorded (Count of all events the student is registered for)
    # Placeholder: Replace 0 with a query like: Registration.objects.filter(student=student_profile).count()
    total_registered = 0

    # 3. Logic to calculate Total Feedback Sent (Count of feedback submitted by the student)
    # Placeholder: Replace 0 with a query like: Feedback.objects.filter(student=student_profile).count()
    total_feedback_sent = 0

    # 4. Logic to find the Next Upcoming Registered Event
    # Placeholder: Replace None with a query like:
    # Registration.objects.filter(student=student_profile, event__date__gte=date.today()).order_by('event__date').first().event
    next_event_data = None

    # --- PLACEHOLDER LOGIC ENDS HERE ---

    template_context = {
        'user_display_name': user_display_name,
        'events_attended_count': events_attended,  # Maps to Total Events Attended (Stat Box 1)
        'total_registered_count': total_registered,  # Maps to Total Attendance Recorded (Stat Box 2)
        'upcoming_events_count': total_feedback_sent,  # Maps to Total Feedback Sent (Stat Box 3)
        'next_event': next_event_data,  # Maps to Upcoming Registered Events section
    }

    if is_ajax:
        return render(request, 'fragments/dashboard_content_student.html', template_context)

    return render(request, 'student_dashboard.html', template_context)