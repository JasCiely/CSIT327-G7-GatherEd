import datetime
from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
import logging  # Import logging for better error handling

# Set up logging
logger = logging.getLogger(__name__)


def format_to_readable_date(date_str):
    if not date_str:
        return 'N/A'
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y').lstrip('0')
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return date_str


def format_to_12hr(time_str):
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            return datetime.datetime.strptime(time_str, fmt).strftime('%I:%M %p').lstrip('0')
        except ValueError:
            continue
    return time_str


def get_event_status(event_date_str, start_time_str, end_time_str):
    if not all([event_date_str, start_time_str, end_time_str]):
        return 'Unknown'
    try:
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()

        def parse_time(ts):
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    return datetime.datetime.strptime(ts, fmt).time()
                except ValueError:
                    continue
            return datetime.time(0, 0)

        now = datetime.datetime.now()
        start_dt = datetime.datetime.combine(event_date, parse_time(start_time_str))
        end_dt = datetime.datetime.combine(event_date, parse_time(end_time_str))

        if now < start_dt:
            return 'Upcoming'
        elif start_dt <= now <= end_dt:
            return 'Active'
        return 'Completed'
    except Exception as e:
        logger.error(f"Error getting event status: {e}")
        return 'Unknown'


@login_required
def manage_events(request):
    """Handles Manage Events display and filtering."""
    is_ajax = request.GET.get('is_ajax') == 'true'
    search_query = request.GET.get('search', '').lower().strip()
    status_filter = request.GET.get('status', 'All').lower()  # Normalize to lowercase for consistency

    try:
        admin_id = str(request.user.adminprofile.id)  # Add check for adminprofile
    except AttributeError:
        logger.error("User does not have an adminprofile.")
        messages.error(request, "User profile not found. Please contact support.")
        return redirect('/admin_dashboard/')  # Or handle appropriately

    cache_key = f"events_{admin_id}"

    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        res = client.table('events').select('*').eq('admin_id', admin_id).order('date').execute()
        data = getattr(res, 'data', []) or []

        events_list = []
        for ev in data:
            event_status = get_event_status(ev.get('date'), ev.get('start_time'), ev.get('end_time'))
            event_name = ev.get('title', 'N/A').lower()  # Normalize for search comparison

            # Apply filters - Note: status_filter is now lowercase
            if (search_query in event_name) and (status_filter == 'all' or status_filter == event_status.lower()):
                events_list.append({
                    'id': ev['id'],
                    'name': ev.get('title', 'N/A'),
                    'description': ev.get('description', 'N/A'),
                    'date': format_to_readable_date(ev.get('date')),
                    'location': ev.get('location', 'N/A'),
                    'start_time': format_to_12hr(ev.get('start_time')),
                    'end_time': format_to_12hr(ev.get('end_time')),
                    'status': event_status,  # Keep original case for frontend
                    'registrations': 0,  # You might want to fetch this dynamically
                    'max_attendees': ev.get('max_attendees', 0),
                })

        cache.set(cache_key, events_list, timeout=60)  # Cache the final filtered list
    except Exception as e:
        logger.error(f"Supabase error: {e}")
        events_list = []  # Ensure it's empty on error

    context = {'events_list': events_list, 'title': 'Manage Events'}

    if is_ajax:
        return render(request, 'fragments/manage_event/manage_events_content.html', context)

    # Render the full template instead of redirecting
    return render(request, 'manage_events.html', context)  # Assuming your full template is named this


@login_required
def modify_event_view(request, event_id):
    """Edit event details (simplified)."""
    if request.method == 'POST':
        # Add more logic here if needed, e.g., update the event
        messages.success(request, "Event updated successfully.")
        # Invalidate cache
        cache_key = f"manage_events_{request.user.adminprofile.id}"
        cache.delete(cache_key)
        cache.delete(f"{cache_key}_refresh")
        return redirect('manage_events')  # Redirect to manage_events view

    # Fetch event details here if needed
    return render(request, 'fragments/manage_event/modify_event_form.html', {'event_id': event_id})