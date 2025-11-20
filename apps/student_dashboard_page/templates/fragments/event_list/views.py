# In your app's views.py (e.g., student_dashboard_app/views.py)
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Count, Case, When, F, Q, Value, BooleanField, IntegerField
from datetime import date, datetime
from django.contrib.auth.decorators import login_required

# NOTE: Ensure these imports are correct for your project structure
from apps.admin_dashboard_page.models import Event
from apps.register_page.models import StudentProfile
from apps.student_dashboard_page.models import Registration


def event_list(request):
    """
    Displays upcoming and active events for the student dashboard.
    Fetches real data using Django ORM.
    """
    current_student = None
    if request.user.is_authenticated:
        try:
            # Fetch the student profile linked to the user
            current_student = StudentProfile.objects.get(user=request.user)
        except StudentProfile.DoesNotExist:
            current_student = None

    today = date.today()
    now = datetime.now().time()

    # 1. Annotate to determine if the current student is registered (if logged in)
    is_registered_annotation = Value(False, output_field=BooleanField())
    if current_student:
        is_registered_annotation = Count(
            Case(
                When(registrations__student=current_student, registrations__status='REGISTERED', then=1),
                output_field=IntegerField(),
            )
        )

    # 2. Annotate with current attendee count
    attendee_count_annotation = Count(
        'registrations',
        filter=Q(registrations__status__in=['REGISTERED', 'ATTENDED']),
        distinct=True
    )

    # 3. Filter for upcoming events
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

    # 4. Build event list with proper statuses
    events_list = []
    for event in upcoming_and_active_events:
        registered_count = getattr(event, 'registered_count', 0)
        is_registered = getattr(event, 'is_registered_by_student', 0) > 0

        is_full = (
                event.max_attendees is not None
                and event.max_attendees > 0
                and registered_count >= event.max_attendees
        )

        # Determine status
        if is_registered:
            status = 'Registered'
        elif is_full:
            status = 'Full'
        else:
            status = 'Available'

        events_list.append({
            'id': event.id,
            'name': event.title,
            'date': event.date.strftime('%b %d, %Y'),
            'time': f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}",
            'organization_name': getattr(event.admin, 'organization_name', 'Unknown'),
            'location': event.location or 'N/A',
            'status': status,
            'short_description': event.description[:100] + '...' if len(event.description) > 100 else event.description,
            'attendee_count': registered_count,
            'capacity': event.max_attendees,
            # Placeholder/Example for image URL
            'image_url': getattr(event, 'image_url', None),
        })

    context = {'events_list': events_list}

    # Handle AJAX vs normal refresh
    is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.GET.get('is_ajax') == 'true'
    )

    if is_ajax:
        # Render ONLY the fragment containing the card grid
        # NOTE: Ensure you have this template path
        return render(request, 'fragments/event_list/event_list_content.html', context)
    else:
        # Redirect to the main dashboard page that includes this fragment
        return redirect('student_dashboard')


def event_details(request, event_id):
    """
    Handles the AJAX request for the full details of a single event for the modal.
    """
    try:
        event = Event.objects.get(pk=event_id)

        data = {
            'event_id': event_id,
            'full_description': event.description,
            'image_url': getattr(event, 'image_url', ''), # Placeholder/Example
        }
        return JsonResponse(data)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)
    except Exception as e:
        print(f"Error fetching event details: {e}")
        return JsonResponse({'error': 'An internal error occurred'}, status=500)


@login_required
def register_event(request, event_id):
    """
    Handles student registration for an event. Requires user authentication and a POST request.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    try:
        event = Event.objects.get(pk=event_id)
        current_student = StudentProfile.objects.get(user=request.user)

        # 1. Capacity Check
        current_registrations = Registration.objects.filter(
            event=event,
            status__in=['REGISTERED', 'ATTENDED']
        ).count()

        if event.max_attendees is not None and event.max_attendees > 0 and current_registrations >= event.max_attendees:
            return JsonResponse({'success': False, 'message': 'Registration failed: Event is full.'}, status=400)

        # 2. Duplicate Registration Check
        if Registration.objects.filter(student=current_student, event=event, status='REGISTERED').exists():
            return JsonResponse({'success': False, 'message': 'You are already registered for this event.'}, status=400)

        # 3. Create Registration Record
        Registration.objects.create(
            event=event,
            student=current_student,
            status='REGISTERED',
        )

        return JsonResponse({
            'success': True,
            'message': f'Successfully registered for {event.title}!',
        })

    except Event.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Event not found.'}, status=404)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Student profile not found. You may need to create one.'}, status=404)
    except Exception as e:
        print(f"Registration error: {e}")
        return JsonResponse({'success': False, 'message': 'An internal error occurred during registration.'},
                            status=500)