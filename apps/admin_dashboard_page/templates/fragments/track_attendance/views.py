from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta
import json
# Assuming these models are correctly linked in your project structure
from apps.admin_dashboard_page.models import Event
from apps.student_dashboard_page.models import Registration


# --- Helper functions for status mapping ---

def map_db_status_to_js(db_status):
    """
    Maps the database Registration status to the frontend display status.
    Uses 'Absent' explicitly when DB status is 'ABSENT'.
    """
    if db_status == 'ATTENDED':
        return 'Present'
    # 🎯 UPDATED: Use the new 'ABSENT' status for display
    elif db_status == 'ABSENT':
        return 'Absent'
    # Note: 'CANCELLED' is now only used if a student manually cancelled registration.
    elif db_status == 'CANCELLED':
        return 'Cancelled'
    return 'Unmarked'  # Maps 'REGISTERED' to 'Unmarked'


def map_js_status_to_db(is_present):
    """
    Maps the frontend boolean (is_present) to the database Registration status.
    🎯 UPDATED: Uses 'ABSENT' when the student is marked as not present.
    """
    return 'ATTENDED' if is_present else 'ABSENT'


def get_attendance_window_status(event):
    """Calculates the current attendance status - recording only during event duration."""
    current_dt = timezone.now()

    # Combine date and time fields and make them timezone aware
    event_start_dt = timezone.make_aware(
        datetime.combine(event.date, event.start_time)
    )

    # Determine the end time
    if event.end_time:
        event_end_dt = timezone.make_aware(
            datetime.combine(event.date, event.end_time)
        )
    else:
        # Default to 2 hours after start time if end time is missing
        event_end_dt = event_start_dt + timedelta(hours=2)

    attendance_enabled = True
    status_message = ""

    # SIMPLE LOGIC: Recording only during event duration
    if current_dt < event_start_dt:
        attendance_enabled = False
        time_until = event_start_dt - current_dt
        hours, remainder = divmod(time_until.total_seconds(), 3600)
        minutes = remainder // 60

        if hours > 0:
            status_message = f"Attendance recording will open at {event_start_dt.strftime('%I:%M %p, %b %d')}"
        else:
            status_message = f"Attendance recording opens in {int(minutes)} minutes at {event_start_dt.strftime('%I:%M %p')}"

    elif current_dt >= event_end_dt:
        attendance_enabled = False
        status_message = f"Attendance recording is closed (event ended at {event_end_dt.strftime('%I:%M %p, %b %d')})"

    return attendance_enabled, status_message


# --- Django Views ---

@login_required
def track_attendance(request):
    """Renders the initial attendance tracking page (or fragment)."""
    is_ajax = request.GET.get('is_ajax') == 'true'

    # Filter events to only show those owned by the current admin
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
        # Simple redirect after POST, typically used for form submission completion
        return redirect('track_attendance')
    else:
        # Check if the request is for the fragment content
        template_name = 'fragments/track_attendance/track_attendance_content.html'

        # If it's a full page load, redirect to the dashboard (as per previous logic)
        if not is_ajax:
            # Assuming 'admin_dashboard' is the name of your main admin dashboard URL
            return redirect('admin_dashboard')

        return render(request, template_name, template_context)


@login_required
@require_http_methods(["GET"])
def get_event_students(request, event_id):
    """API to fetch students, now including event status for frontend control."""

    try:
        # Authorize: Check if the user owns the event
        event = get_object_or_404(
            Event.objects.filter(admin__user=request.user),
            pk=event_id
        )
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found or unauthorized.'}, status=404)

    # Get attendance status
    attendance_enabled, status_message = get_attendance_window_status(event)

    registration_records = Registration.objects.filter(event=event).select_related('student')

    students_data = []
    for record in registration_records:
        # Uses the updated function to display 'Absent'
        js_status = map_db_status_to_js(record.status)

        students_data.append({
            'student_id': record.student.pk,
            # Assuming 'name' and 'cit_id' are attributes on the Student model linked via Registration
            'name': record.student.name,
            'identifier': record.student.cit_id,
            'status': js_status,
            'is_recorded': js_status != 'Unmarked'
        })

    return JsonResponse({
        'students': students_data,
        'attendance_enabled': attendance_enabled,
        'status_message': status_message
    })


@login_required
@require_http_methods(["POST"])
def record_attendance(request):
    """
    API to update a student's attendance status for an event.
    (CRITICAL: Enforces time restriction on the server side.)
    """

    # Handle JSON or form-encoded data
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON.")
    else:
        # Fallback for standard form post, though JS uses JSON/data object generally
        data = request.POST

    student_pk = data.get('student_id')
    event_id = data.get('event_id')
    is_present_str = data.get('is_present')
    # Convert string boolean to actual boolean
    is_present = str(is_present_str).lower() == 'true'

    if not all([student_pk, event_id, is_present_str is not None]):
        return HttpResponseBadRequest("Missing required fields.")

    try:
        # 1. Authorization: Verify Event ownership
        event = get_object_or_404(
            Event.objects.filter(admin__user=request.user),
            pk=event_id
        )

        # 2. CRITICAL CHECK: Enforce the attendance window
        attendance_enabled, status_message = get_attendance_window_status(event)

        if not attendance_enabled:
            return JsonResponse({'error': status_message}, status=403)

        # 3. Get the specific Registration Record
        record = get_object_or_404(
            Registration,
            event=event,
            student_id=student_pk
        )

        # 4. Update the status and timestamp
        db_new_status = map_js_status_to_db(is_present) # Will be 'ATTENDED' or 'ABSENT'
        js_new_status = map_db_status_to_js(db_new_status) # Will be 'Present' or 'Absent'

        record.status = db_new_status

        # Update timestamps based on the new status
        if db_new_status == 'ATTENDED':
            record.attended_at = timezone.now()
            # Clear other tracking fields
            record.absent_marked_at = None
            record.cancelled_at = None
        elif db_new_status == 'ABSENT':
            record.absent_marked_at = timezone.now() # 🎯 UPDATED: Use the new field
            # Clear other tracking fields
            record.attended_at = None
            record.cancelled_at = None
        # If status is set back to 'REGISTERED' (which is not handled by this toggle, but for completeness):
        # else:
        #     record.attended_at = None
        #     record.absent_marked_at = None
        #     record.cancelled_at = None

        record.save()

        return JsonResponse({
            'message': 'Attendance updated successfully.',
            'new_status': js_new_status # This will return 'Present' or 'Absent'
        })

    except Event.DoesNotExist:
        return HttpResponseForbidden("Event not found or unauthorized.")
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Student not registered for this event.'}, status=404)
    except Exception as e:
        # Log the error for debugging
        print(f"Error recording attendance: {e}")
        return JsonResponse({'error': 'Failed to save attendance due to server error.'}, status=500)