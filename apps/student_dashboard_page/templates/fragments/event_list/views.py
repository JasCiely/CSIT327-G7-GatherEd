from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Count, Case, When, Q, Value, BooleanField, IntegerField
from datetime import date, datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import traceback
import uuid

# Assuming these models are correctly imported based on your project structure
from apps.admin_dashboard_page.models import Event
from apps.register_page.models import StudentProfile
from apps.student_dashboard_page.models import Registration


# === Helper Function: Determines Event Status for Student ===
def get_registration_status_from_event(event, registered_count, is_registered_by_student):
    """
    Determines the registration status for a student event, respecting manual overrides.

    CRUCIAL: The is_registered_by_student check is prioritized above all other checks.
    This now properly handles all registration statuses (REGISTERED, ATTENDED, ABSENT).
    """
    manual = (event.manual_status_override or 'AUTO').upper()
    max_attendees = event.max_attendees or 0
    now = datetime.now()

    # 1. 🏆 Highest Priority: Student's Personal Registration Status
    # If the student has ANY active registration (not CANCELLED), return 'Registered'
    if is_registered_by_student:
        return 'Registered'

    # 2. Manual Status Override Check (Temporary Closure/Opening)
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
            # Registration is manually opened until manual_limit_dt
            close_time_str = manual_limit_dt.strftime('%I:%M %p') if event.manual_close_time else None
            close_date_str = manual_limit_dt.strftime('%b %d')

            is_full = (max_attendees > 0 and registered_count >= max_attendees)

            if is_full:
                # If full, display 'Full' but mention the temporary nature
                if close_time_str:
                    return f'Full (Manual Open Until {close_time_str} {close_date_str})'
                else:
                    return f'Full (Manual Open Until {close_date_str})'
            else:
                # Available and display the temporary nature
                if close_time_str:
                    return f'Available (Until {close_time_str} {close_date_str})'
                else:
                    return f'Available (Until {close_date_str})'

        elif manual == 'CLOSED_MANUAL':
            # Registration is manually closed until manual_limit_dt
            close_time_str = event.manual_close_time.strftime('%I:%M %p') if event.manual_close_time else None
            close_date_str = event.manual_close_date.strftime('%b %d')

            if close_time_str:
                return f'Temporarily Closed (Until {close_time_str} {close_date_str})'
            else:
                return f'Temporarily Closed (Until {close_date_str})'

    # 3. Event Life Status and Hard Closure Checks
    # (Only for non-registered students)

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
        # Event is currently ongoing (active)
        if max_attendees and registered_count >= max_attendees:
            # If full while ongoing, show Full
            return 'Full'
        else:
            # Otherwise, show ongoing status (which closes registration)
            return 'Closed – Event Ongoing'

    if manual == 'ONGOING':
        return 'Closed – Event Ongoing'

    # 4. Standard Capacity Check (AUTO or Expired Override, NOT Registered)

    is_full = (
            max_attendees > 0
            and registered_count >= max_attendees
    )

    if is_full:
        return 'Full'

    return 'Available'

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

    # FIXED: Annotation to check for ALL active registration statuses
    is_registered_annotation = Value(False, output_field=BooleanField())
    if current_student:
        # Check if the student has any active registration status
        is_registered_annotation = Count(
            Case(
                When(
                    registrations__student=current_student,
                    registrations__status__in=['REGISTERED', 'ATTENDED', 'ABSENT'],
                    then=1
                ),
                output_field=IntegerField(),
            )
        )

    # Count all registrations that consume capacity (registered and attended)
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
        # Note: is_registered_by_student is a Count, so check if it's > 0
        is_registered = getattr(event, 'is_registered_by_student', 0) > 0

        # Use the updated logic
        final_status = get_registration_status_from_event(
            event,
            registered_count,
            is_registered
        )

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
            'picture_url': event.picture_url.rstrip('?') if event.picture_url else None,
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
    Handles student registration for an event.
    The capacity check is now UNCONDITIONAL, meaning registration is blocked if full,
    even if the manual override is 'OPEN_MANUAL'.
    """
    print(f"=== REGISTRATION DEBUG START ===")

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    try:
        # Step 1: Password Verification
        try:
            data = json.loads(request.body)
            submitted_password = data.get('password')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON format.'}, status=400)

        if not submitted_password:
            return JsonResponse({'success': False, 'message': 'Password verification is required.'}, status=400)

        user = request.user
        authenticated_user = authenticate(username=user.username, password=submitted_password)

        if authenticated_user is None:
            return JsonResponse({
                'success': False,
                'message': 'Password verification failed. The password entered is incorrect.',
                'code': 'INVALID_PASSWORD'
            }, status=401)
        print("✓ Password verified successfully")

        # Step 2: Get event and student profile
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Event not found.'}, status=404)

        try:
            current_student = StudentProfile.objects.get(user=authenticated_user)
        except StudentProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Student profile not found. Please ensure you are logged in with a valid student account.'
            }, status=403)

        # --------------------------------------------------------------------
        # Step 3: 🛑 Comprehensive Re-registration Check
        # Block re-registration if any registration exists that is NOT CANCELLED.
        existing_active_registration = Registration.objects.filter(
            student=current_student,
            event=event,
            status__in=['REGISTERED', 'ATTENDED', 'ABSENT']
        ).exists()

        if existing_active_registration:
            print("ERROR: Registration found with status other than CANCELLED.")
            return JsonResponse({
                'success': False,
                'message': 'You have already registered for this event. You cannot register again unless your prior registration was officially **Cancelled**.'
            }, status=400)
        print("✓ No non-cancelled prior registration found.")
        
        # Check if there's a CANCELLED registration that can be reactivated
        cancelled_registration = Registration.objects.filter(
            student=current_student,
            event=event,
            status='CANCELLED'
        ).first()
        # --------------------------------------------------------------------

        # --- Step 3.5: Manual Status and Timing Check ---
        now = datetime.now()
        is_manual_open = False

        if (
                event.manual_status_override in ['OPEN_MANUAL', 'CLOSED_MANUAL']
                and event.manual_close_date
        ):
            close_datetime = datetime.combine(event.manual_close_date, event.manual_close_time or datetime.min.time())

            # Check if the manual override is currently active (i.e., not expired)
            if now < close_datetime:
                if event.manual_status_override == 'CLOSED_MANUAL':
                    return JsonResponse({
                        'success': False,
                        'message': 'Registration for this event is currently closed by the organizer.'
                    }, status=400)

                elif event.manual_status_override == 'OPEN_MANUAL':
                    is_manual_open = True
                    print("✓ Manual OPEN_MANUAL override is active.")

        # --- Step 3.6: Standard Timing Check (Conditional) ---
        # Block registration if the event has started, UNLESS manual open is active
        if not is_manual_open:
            event_start_dt = datetime.combine(event.date, event.start_time)
            event_end_dt = datetime.combine(event.date, event.end_time or event.start_time)
            if event_end_dt < event_start_dt:
                event_end_dt += timedelta(days=1)

            if now >= event_start_dt:
                return JsonResponse({
                    'success': False,
                    'message': 'Registration is closed because the event is currently ongoing or has passed.'
                }, status=400)

        # Step 4: Capacity check (Unconditional)
        current_registrations = Registration.objects.filter(
            event=event,
            status__in=['REGISTERED', 'ATTENDED']
        ).count()

        # 🛑 MODIFIED: Capacity check is now UNCONDITIONAL. If the event is full, registration is blocked.
        if event.max_attendees is not None and event.max_attendees > 0 and current_registrations >= event.max_attendees:
            print(f"ERROR: Registration blocked due to capacity (Count: {current_registrations}, Max: {event.max_attendees}).")
            return JsonResponse({'success': False, 'message': 'Registration failed: Event is full.'}, status=400)

        # Step 5: Create or reactivate registration
        if cancelled_registration:
            # Reactivate the cancelled registration
            cancelled_registration.status = 'REGISTERED'
            cancelled_registration.registered_at = timezone.now()
            cancelled_registration.cancelled_at = None
            cancelled_registration.save()
            registration = cancelled_registration
            print(f"✓ Cancelled registration reactivated: {registration.id}")
        else:
            # Create new registration
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
        print(f"FATAL ERROR: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        print("=== REGISTRATION DEBUG END ===")

        return JsonResponse({
            'success': False,
            'message': f'An internal server error occurred: {str(e)}'
        }, status=500)