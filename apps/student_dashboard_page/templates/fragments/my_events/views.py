from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.db import transaction, IntegrityError
from django.contrib.auth import authenticate
from django.utils import timezone  # Use Django's timezone utility
from datetime import datetime, timedelta, date
import json
import traceback

from apps.admin_dashboard_page.models import Event
from apps.register_page.models import StudentProfile
from apps.student_dashboard_page.models import Registration


# --- UTILITY FUNCTION ---

def get_registration_status_for_display(registration, event):
    """
    Determines the simplified status of the *student's registration* for display.
    Prioritizes registration status and event lifecycle, correctly mapping
    database statuses (ATTENDED, ABSENT, REGISTERED) to student view statuses
    (Attended, Absent, Did Not Attend, Registered, Cancelled).
    """
    now = timezone.now()
    event_date = event.date

    # 1. Check Registration Status (Highest priority - finalized status)
    if registration.status == 'CANCELLED':
        return 'Cancelled'

    # Explicitly map attendance statuses
    if registration.status == 'ATTENDED':
        return 'Attended'

    if registration.status == 'ABSENT':
        return 'Absent'

    # 2. Calculate Event End Time (needed for "Did Not Attend" check)
    try:
        # Use timezone.make_aware if event_start_time is naive
        # We assume event.date, event.start_time are simple date/time objects
        event_start_dt = timezone.make_aware(datetime.combine(event_date, event.start_time))

        if event.end_time:
            event_end_dt = timezone.make_aware(datetime.combine(event_date, event.end_time))
        else:
            # Fallback for events without an explicit end time (e.g., +2 hours)
            event_end_dt = event_start_dt + timedelta(hours=2)

    except Exception:
        # Should not happen if data is clean, but protects against timezone errors
        return 'Status Error'

    # 3. Check for 'Did Not Attend' (Only applies to 'REGISTERED' status)
    if registration.status == 'REGISTERED':
        if now > event_end_dt:
            # Event has finished, and attendance was never recorded (ATTENDED/ABSENT)
            return 'Did Not Attend'

        # Check if the event is currently ongoing
        if event_start_dt <= now <= event_end_dt:
            return 'Ongoing'

    # 4. Check for manual overrides (should typically supersede 'Ongoing' if set)
    manual_status = (event.manual_status_override or 'AUTO').upper()
    if manual_status == 'CLOSED_MANUAL':
        return 'Temporarily Closed'

    # 5. Default: Event is in the future
    return 'Registered'


# --- STUDENT DASHBOARD VIEWS ---

@login_required
def my_events(request):
    """
    Displays the list of events the student is registered for.
    """
    is_ajax = request.GET.get('is_ajax') == 'true'

    try:
        student = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        context = {"registered_events_data": []}
        if is_ajax:
            return render(request, "fragments/my_events/my_events_content.html", context)
        return render(request, 'student_dashboard.html', context)

    # Query Registrations for the student (including 'CANCELLED' status)
    registrations = (
        Registration.objects
        .filter(student=student)
        .select_related('event', 'event__admin')
        # Annotate the Registration with the total attendee count
        .annotate(
            event_attendee_count=Count(
                'event__registrations',
                filter=Q(event__registrations__status__in=['REGISTERED', 'ATTENDED']),
                distinct=True
            )
        )
        .order_by('-registered_at')
    )

    registered_events_list = []

    for registration in registrations:
        event = registration.event
        registered_count = registration.event_attendee_count

        # Use the refined status function
        final_status = get_registration_status_for_display(
            registration,
            event
        )

        org_name = getattr(event.admin, 'organization_name', 'Unknown') if event.admin else 'Unknown'

        # Determine time display for consistency
        start_time_str = event.start_time.strftime('%I:%M %p')
        end_time_str = event.end_time.strftime('%I:%M %p') if event.end_time else 'End time N/A'
        time_display = f"{start_time_str} - {end_time_str}"

        # Shorten description
        description = event.description or 'No description available'
        short_description = description[:100] + '...' if len(description) > 100 else description

        registered_events_list.append({
            'id': event.id,
            'name': event.title,
            'date': event.date.strftime('%b %d, %Y'),
            'time': time_display,
            'organization_name': org_name,
            'location': event.location or 'N/A',
            # This 'status' field now holds 'Attended', 'Absent', 'Did Not Attend', 'Registered', or 'Cancelled'
            'status': final_status,
            'short_description': short_description,
            'full_description': description,
            'picture_url': event.picture_url,
            'attendee_count': registered_count,
            'capacity': event.max_attendees,
            'registration': registration
        })

    context = {
        "registered_events_data": registered_events_list
    }

    if is_ajax:
        return render(request, "fragments/my_events/my_events_content.html", context)

    return render(request, 'student_dashboard.html', context)


@login_required
def cancel_registration(request, registration_id):
    """
    Handles the AJAX POST request to cancel a student's event registration.
    """
    print(f"DEBUG: Cancel registration called with ID: {registration_id}")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: User: {request.user}")

    if request.method != 'POST':
        print("DEBUG: Invalid method - not POST")
        return HttpResponseBadRequest('Invalid request method.')

    try:
        # 1. Get Registration Object with detailed debugging
        print(f"DEBUG: Looking for registration with ID: {registration_id}")

        try:
            registration = Registration.objects.get(id=registration_id)
            print(f"DEBUG: Found registration: {registration}")
            print(f"DEBUG: Registration student: {registration.student.user}")
            print(f"DEBUG: Registration event: {registration.event.title}")
            print(f"DEBUG: Registration status: {registration.status}")
        except Registration.DoesNotExist:
            print(f"DEBUG: Registration with ID {registration_id} does not exist in database")
            all_reg_ids = Registration.objects.values_list('id', flat=True)
            print(f"DEBUG: All registration IDs in DB: {list(all_reg_ids)}")
            return HttpResponseNotFound('Registration record not found.')

        # 2. Authorization Check
        if registration.student.user != request.user:
            print(f"DEBUG: Authorization failed - user mismatch")
            return HttpResponseForbidden('You are not authorized to cancel this registration.')

        # 3. Initial Status Check
        if registration.status != 'REGISTERED':
            print(f"DEBUG: Invalid status - current status: {registration.status}")
            return JsonResponse({
                'success': False,
                'message': f'Cannot cancel registration: status is already {registration.status}.'
            }, status=400)

        # 4. Event Timing Check
        event = registration.event
        now = timezone.now()  # Use timezone.now() for consistency
        event_start_dt = timezone.make_aware(datetime.combine(event.date, event.start_time))

        print(f"DEBUG: Event timing check:")
        print(f"DEBUG: - Event: {event.title}")
        print(f"DEBUG: - Event start datetime: {event_start_dt}")
        print(f"DEBUG: - Current datetime: {now}")
        print(f"DEBUG: - Can cancel? {now < event_start_dt}")

        if now >= event_start_dt:
            return JsonResponse({
                'success': False,
                'message': f'Cannot cancel registration for event "{event.title}" that has already started.'
            }, status=400)

        # 5. Password Verification
        try:
            data = json.loads(request.body)
            password = data.get('password')
            print(f"DEBUG: Password received: {'Yes' if password else 'No'}")
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON decode error: {e}")
            return JsonResponse({'success': False, 'message': 'Invalid data format.'}, status=400)

        if not password:
            return JsonResponse({
                'success': False,
                'message': 'Password is required for cancellation verification.'
            }, status=401)

        user = authenticate(username=request.user.username, password=password)
        if user is None:
            print(f"DEBUG: Password authentication failed")
            return JsonResponse({
                'success': False,
                'message': 'Verification Failed. The password you entered is incorrect.'
            }, status=401)

        # 6. Execute Cancellation
        print(f"DEBUG: Proceeding with cancellation...")
        with transaction.atomic():
            registration.status = 'CANCELLED'
            registration.cancelled_at = timezone.now()  # Use timezone.now()
            registration.save()
            print(f"DEBUG: Registration cancelled successfully")

        return JsonResponse({
            'success': True,
            'message': f'Successfully cancelled registration for "{event.title}".',
            'registration_id': str(registration_id),
            'new_status_display': 'Cancelled'
        })

    except Exception as e:
        print(f"DEBUG: Unexpected error: {str(e)}")
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'An unexpected server error occurred during cancellation.'
        }, status=500)