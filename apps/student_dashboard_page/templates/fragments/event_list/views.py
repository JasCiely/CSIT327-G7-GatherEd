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

    upcoming_and_active_events = (
        Event.objects
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

        is_full = (
            event.max_attendees is not None
            and event.max_attendees > 0
            and registered_count >= event.max_attendees
        )

        if is_registered:
            status = 'Registered'
        elif is_full:
            status = 'Full'
        else:
            status = 'Available'

        org_name = getattr(event.admin, 'organization_name', 'Unknown') if event.admin else 'Unknown'

        events_list.append({
            'id': event.id,
            'name': event.title,
            'date': event.date.strftime('%b %d, %Y'),
            'time': f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}",
            'organization_name': org_name,
            'location': event.location or 'N/A',
            'status': status,
            'short_description': event.description[:100] + '...' if event.description and len(event.description) > 100 else event.description or 'No description available',
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
    Handles student registration for an event with enhanced debugging.
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
        # Parse JSON data
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

        # Verify password
        user = request.user
        print(f"Attempting to authenticate user: {user.username}")
        authenticated_user = authenticate(username=user.username, password=submitted_password)

        if authenticated_user is None:
            print("ERROR: Password authentication failed")
            return JsonResponse({
                'success': False,
                'message': 'Password verification failed. The password entered is incorrect.',
                'code': 'INVALID_PASSWORD'
            }, status=401)

        print("✓ Password verified successfully")

        # Get event
        try:
            event = Event.objects.get(pk=event_id)
            print(f"✓ Event found: {event.title} (ID: {event.id})")
        except Event.DoesNotExist:
            print(f"ERROR: Event not found with ID: {event_id}")
            return JsonResponse({'success': False, 'message': 'Event not found.'}, status=404)
        except Exception as e:
            print(f"ERROR: Unexpected error fetching event: {e}")
            return JsonResponse({'success': False, 'message': 'Error accessing event.'}, status=500)

        # Get student profile
        try:
            current_student = StudentProfile.objects.get(user=authenticated_user)
            print(f"✓ Student profile found: {current_student.name}")
        except StudentProfile.DoesNotExist:
            print("ERROR: Student profile not found")
            return JsonResponse({
                'success': False,
                'message': 'Student profile not found. Please ensure you are logged in with a valid student account.'
            }, status=403)

        # Capacity check
        current_registrations = Registration.objects.filter(
            event=event,
            status__in=['REGISTERED', 'ATTENDED']
        ).count()

        print(f"Current registrations: {current_registrations}")
        print(f"Max attendees: {event.max_attendees}")

        if event.max_attendees is not None and event.max_attendees > 0 and current_registrations >= event.max_attendees:
            print("ERROR: Event is full")
            return JsonResponse({'success': False, 'message': 'Registration failed: Event is full.'}, status=400)

        # Duplicate registration check
        existing_registration = Registration.objects.filter(
            student=current_student,
            event=event,
            status='REGISTERED'
        ).exists()

        if existing_registration:
            print("ERROR: Already registered")
            return JsonResponse({'success': False, 'message': 'You are already registered for this event.'}, status=400)

        # Create registration
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
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        print("=== REGISTRATION DEBUG END ===")

        return JsonResponse({
            'success': False,
            'message': f'An internal server error occurred: {str(e)}'
        }, status=500)