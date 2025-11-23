from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Count, Case, When, Q, Value, BooleanField, IntegerField
from datetime import date, datetime
from django.contrib.auth.decorators import login_required
import json
import traceback

from apps.admin_dashboard_page.models import Event
from apps.register_page.models import StudentProfile
from apps.student_dashboard_page.models import Registration


def get_registration_status_from_event(event, registered_count, is_registered_by_student):
    """
    Determines the registration status for a student event, respecting manual overrides.
    """
    manual = (event.manual_status_override or 'AUTO').upper()
    max_attendees = event.max_attendees or 0

    # 1. Manual Status Override Check
    now = datetime.now()
    manual_limit_dt = None

    if manual in ['OPEN_MANUAL', 'CLOSED_MANUAL'] and event.manual_close_date:
        # Combine date and time, using midnight if time is missing
        close_time = event.manual_close_time or datetime.min.time()
        manual_limit_dt = datetime.combine(event.manual_close_date, close_time)

        # Check for expiration
        if manual_limit_dt and now >= manual_limit_dt:
            # If expired, revert to AUTO logic
            manual = 'AUTO'
        elif manual == 'OPEN_MANUAL':
            return 'Available'
        elif manual == 'CLOSED_MANUAL':
            # 💡 NEW INDICATION: Specific message for temporary closure
            close_time_str = manual_limit_dt.strftime('%I:%M %p') if event.manual_close_time else None
            close_date_str = manual_limit_dt.strftime('%b %d')

            if close_time_str:
                return f'Temporarily Closed (Until {close_time_str} {close_date_str})'
            else:
                return f'Temporarily Closed (Until {close_date_str})'

    # 2. Event Life Status and Hard Closure Checks

    # Combine date and time for comparison
    event_start_dt = datetime.combine(event.date, event.start_time)
    event_end_dt = datetime.combine(event.date, event.end_time or event.start_time)
    if event_end_dt < event_start_dt:  # Handle end time on the next day
        event_end_dt += timedelta(days=1)

    is_completed = now >= event_end_dt
    is_active = now >= event_start_dt and now < event_end_dt

    if is_completed:
        return 'Completed'

    if is_active:
        if max_attendees and registered_count >= max_attendees:
            return 'Full'
        else:
            # Standard closure for active events
            return 'Closed – Event Ongoing'

    if manual == 'ONGOING':
        return 'Closed – Event Ongoing'

    # 3. Standard Registration/Capacity Check (AUTO or Expired Override)

    if is_registered_by_student:
        return 'Registered'

    is_full = (
            max_attendees > 0
            and registered_count >= max_attendees
    )

    if is_full:
        return 'Full'

    return 'Available'


# ---------------------------------------------------------------------

@login_required
def event_list(request):
    """
    Displays upcoming and active events for the student dashboard.
    """
    current_student = None
    if request.user.is_authenticated:
        try:
            current_student = StudentProfile.objects.get(user_id=request.user.pk)
        except StudentProfile.DoesNotExist:
            current_student = None
        except Exception:
            current_student = None

    today = date.today()
    now = datetime.now().time()

    # Annotations for efficient fetching
    is_registered_annotation = Value(False, output_field=BooleanField())
    if current_student:
        is_registered_annotation = Count(
            Case(
                When(registrations__student=current_student, registrations__status='REGISTERED', then=1),
                output_field=IntegerField(),
            )
        )

    attendee_count_annotation = Count(
        'registrations',
        filter=Q(registrations__status__in=['REGISTERED', 'ATTENDED']),
        distinct=True
    )

    # Fetch all relevant fields including manual override fields
    upcoming_and_active_events = (
        Event.objects
        # Filter for upcoming/active events based on standard time
        .filter(Q(date__gt=today) | Q(date=today, end_time__gte=now))
        .select_related('admin')
        .annotate(
            registered_count=attendee_count_annotation,
            is_registered_by_student=is_registered_annotation
        )
        .order_by('date', 'start_time')
    )

    events_list = []
    for event in upcoming_and_active_events:
        registered_count = getattr(event, 'registered_count', 0)
        is_registered = getattr(event, 'is_registered_by_student', 0) > 0

        # --- Use the updated logic ---
        final_status = get_registration_status_from_event(
            event,
            registered_count,
            is_registered
        )
        # ---------------------------

        org_name = getattr(event.admin, 'organization_name', 'Unknown') if event.admin else 'Unknown'

        events_list.append({
            'id': event.id,
            'name': event.title,
            'date': event.date.strftime('%b %d, %Y'),
            'time': f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}",
            'organization_name': org_name,
            'location': event.location or 'N/A',
            # Use the calculated final_status
            'status': final_status,
            'short_description': event.description[:100] + '...' if event.description and len(
                event.description) > 100 else event.description or 'No description available',
            'full_description': event.description or 'No description available',
            'picture_url': event.picture_url,
            'attendee_count': registered_count,
            'capacity': event.max_attendees,
        })

    context = {'events_list': events_list}

    is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.GET.get('is_ajax') == 'true'
    )

    if is_ajax:
        return render(request, 'fragments/event_list/event_list_content.html', context)
    else:
        return render(request, 'student_dashboard.html', context)

@login_required
def register_event(request, event_id):
    """
    Handles student registration for an event, incorporating manual status override.
    """
    print(f"=== REGISTRATION DEBUG START ===")
    print(f"Method: {request.method}")
    print(f"Event ID: {event_id} (Type: {type(event_id)})")
    print(f"User: {request.user}")
    print(f"Authenticated: {request.user.is_authenticated}")

    if request.method != 'POST':
        print("ERROR: Wrong method")
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    try:
        # Step 1: Parse JSON and verify password
        try:
            data = json.loads(request.body)
            submitted_password = data.get('password')
            print(f"Password provided: {bool(submitted_password)}")
        except json.JSONDecodeError as e:
            print(f"JSON Error: {e}")
            return JsonResponse({'success': False, 'message': 'Invalid JSON format.'}, status=400)

        if not submitted_password:
            print("ERROR: No password provided")
            return JsonResponse({'success': False, 'message': 'Password verification is required.'}, status=400)

        user = request.user
        authenticated_user = authenticate(username=user.username, password=submitted_password)

        if authenticated_user is None:
            print("ERROR: Password authentication failed")
            return JsonResponse({
                'success': False,
                'message': 'Password verification failed. The password entered is incorrect.',
                'code': 'INVALID_PASSWORD'
            }, status=401)
        print("✓ Password verified successfully")

        # Step 2: Get event and student profile
        try:
            event = Event.objects.get(pk=event_id)
            print(f"✓ Event found: {event.title} (ID: {event.id})")
        except Event.DoesNotExist:
            print(f"ERROR: Event not found with ID: {event_id}")
            return JsonResponse({'success': False, 'message': 'Event not found.'}, status=404)

        try:
            current_student = StudentProfile.objects.get(user=authenticated_user)
            print(f"✓ Student profile found: {current_student.name}")
        except StudentProfile.DoesNotExist:
            print("ERROR: Student profile not found")
            return JsonResponse({
                'success': False,
                'message': 'Student profile not found. Please ensure you are logged in with a valid student account.'
            }, status=403)

        # --- Manual Status Check ---
        now = datetime.now()
        is_manual_override_expired = False

        # Check for manual closure expiration
        if (
            event.manual_status_override in ['OPEN_MANUAL', 'CLOSED_MANUAL']
            and event.manual_close_date
        ):
            close_datetime = datetime.combine(event.manual_close_date, event.manual_close_time or datetime.min.time())
            if now > close_datetime:
                is_manual_override_expired = True
                print("Manual override has expired.")


        if event.manual_status_override == 'CLOSED_MANUAL' and not is_manual_override_expired:
            print("ERROR: Registration is manually closed.")
            return JsonResponse({
                'success': False,
                'message': 'Registration for this event is currently closed by the organizer.'
            }, status=400)

        if event.manual_status_override == 'ONGOING':
            print("ERROR: Event is currently ongoing/past.")
            return JsonResponse({
                'success': False,
                'message': 'Registration is closed because the event is ongoing or has passed.'
            }, status=400)

        # If it's 'OPEN_MANUAL' and not expired, or 'AUTO', proceed to checks.

        # Step 3: Capacity check
        current_registrations = Registration.objects.filter(
            event=event,
            status__in=['REGISTERED', 'ATTENDED']
        ).count()

        print(f"Current registrations: {current_registrations}")
        print(f"Max attendees: {event.max_attendees}")

        if event.max_attendees is not None and event.max_attendees > 0 and current_registrations >= event.max_attendees:
            print("ERROR: Event is full")
            return JsonResponse({'success': False, 'message': 'Registration failed: Event is full.'}, status=400)

        # Step 4: Duplicate registration check
        existing_registration = Registration.objects.filter(
            student=current_student,
            event=event,
            status='REGISTERED'
        ).exists()

        if existing_registration:
            print("ERROR: Already registered")
            return JsonResponse({'success': False, 'message': 'You are already registered for this event.'}, status=400)

        # Step 5: Create registration
        registration = Registration.objects.create(
            event=event,
            student=current_student,
            status='REGISTERED',
        )

        print(f"✓ Registration created: {registration.id}")
        print("=== REGISTRATION SUCCESSFUL ===")

        return JsonResponse({
            'success': True,
            'message': f'Successfully registered for {event.title}!',
        })

    except Exception as e:
        # ... (error handling remains the same)
        print(f"FATAL ERROR: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        print("=== REGISTRATION DEBUG END ===")

        return JsonResponse({
            'success': False,
            'message': f'An internal server error occurred: {str(e)}'
        }, status=500)