import datetime
import traceback
from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse


# --- Helper Functions (format_to_readable_date, format_to_12hr, get_event_status) ---
def format_to_readable_date(date_str):
    if not date_str: return 'N/A'
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        return date_obj.strftime('%B %d, %Y').lstrip('0')
    except Exception: return date_str


def format_to_12hr(time_str):
    try:
        dt_obj = datetime.datetime.strptime(time_str, '%H:%M:%S')
        return dt_obj.strftime('%I:%M %p').lstrip('0')
    except ValueError:
        try:
            dt_obj = datetime.datetime.strptime(time_str, '%H:%M')
            return dt_obj.strftime('%I:%M %p').lstrip('0')
        except: return time_str


def get_event_status(event_date_str, start_time_str, end_time_str):
    if not all([event_date_str, start_time_str, end_time_str]): return 'Unknown'
    try:
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
        def parse_time(time_str):
            for fmt in ('%H:%M:%S', '%H:%M'):
                try: return datetime.datetime.strptime(time_str, fmt).time()
                except ValueError: continue
            raise ValueError(f"Time string '{time_str}' does not match expected formats.")
        start_time = parse_time(start_time_str)
        end_time = parse_time(end_time_str)
        event_start_dt = datetime.datetime.combine(event_date, start_time)
        event_end_dt = datetime.datetime.combine(event_date, end_time)
        now = datetime.datetime.now()
        if now < event_start_dt: return 'Upcoming'
        elif event_start_dt <= now <= event_end_dt: return 'Active'
        elif now > event_end_dt: return 'Completed'
        return 'Unknown'
    except Exception as e:
        print(f"Error determining event status for {event_date_str}: {e}")
        return 'Unknown'
# -----------------------------------------------------------------------------

def _fetch_single_event(event_id, admin_client):
    """Fetches full details for one event and formats the data."""
    try:
        fetch_result = admin_client.table('events') \
            .select('id, title, description, date, location, start_time, end_time, max_attendees') \
            .eq('id', event_id) \
            .single() \
            .execute()
    except Exception as e:
        print(f"Supabase fetch error for ID {event_id}: {e}")
        return None

    data = getattr(fetch_result, 'data', None)
    if not data:
        print(f"No event data returned from Supabase for ID: {event_id}")
        return None

    date_str = data.get('date', '')
    start_time_str = data.get('start_time', '')
    end_time_str = data.get('end_time', '')
    event_status = get_event_status(date_str, start_time_str, end_time_str)
    current_registrations_count = 0 # Placeholder: Integrate registration count here

    return {
        'id': data['id'],
        'name': data.get('title', 'N/A'),
        'description': data.get('description', 'No description provided.'),
        'date': format_to_readable_date(date_str),
        'location': data.get('location', 'N/A'),
        'start_time': format_to_12hr(start_time_str),
        'end_time': format_to_12hr(end_time_str),
        'max_attendees': data.get('max_attendees', 0) or 0,
        'registrations': current_registrations_count,
        'status': event_status,
    }


@login_required
def get_event_details_html(request, event_id):
    """AJAX endpoint to fetch and render the event details fragment."""
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return HttpResponse("Unauthorized", status=403)

    print(f"Received AJAX request for event ID: {event_id}") # Confirming data is received

    try:
        admin_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

        event_data = _fetch_single_event(event_id, admin_client)

        if not event_data:
            return HttpResponse('<div style="color: red; padding: 20px;">Error 404: Event not found. Check the ID in Supabase.</div>', status=404)

        # Renders ONLY the fragment HTML, which is injected into the details panel
        return render(request, 'fragments/manage_event/event_details_fragment.html', {'event': event_data})

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"CRITICAL ERROR in get_event_details_html: {e}\n{error_trace}")
        return HttpResponse('<div style="color: red; padding: 20px;">Error 500: Server failed to load details. Check the Django console.</div>', status=500)


@login_required
def manage_events(request):
    """Main view for the manage events page (loads the list only)."""
    events_list = []
    is_ajax = request.GET.get('is_ajax', False)

    template_context = {
        'events_list': events_list,
        'title': 'Manage Events',
    }

    try:
        current_admin_id = request.user.adminprofile.id
        admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        fetch_result = admin_client.table('events') \
            .select('id, title, date, start_time, end_time') \
            .eq('admin_id', str(current_admin_id)) \
            .order('date', desc=False) \
            .execute()

        if hasattr(fetch_result, 'error') and fetch_result.error:
            error_msg = fetch_result.error.get('message', 'Unknown Supabase error')
            raise Exception(f"Supabase Client Error: {error_msg}")

        data = getattr(fetch_result, 'data', [])
        if data is None: data = []

        for event in data:
            date_str = event.get('date', '')
            start_time_str = event.get('start_time', '')
            end_time_str = event.get('end_time', '')
            event_status = get_event_status(date_str, start_time_str, end_time_str)
            current_registrations_count = 0

            events_list.append({
                'id': event['id'],
                'name': event.get('title', 'N/A'),
                'date': format_to_readable_date(date_str),
                'registrations': current_registrations_count,
                'status': event_status,
            })

        template_context['events_list'] = events_list

    except Exception as e:
        print(f"Error fetching events from Supabase: {e}")
        messages.error(request,
                       "Failed to load events due to a critical server error. Check the Django console for details.")

    if is_ajax:
        return render(request, 'fragments/manage_event/manage_events_content.html', template_context)

    return render(request, 'admin_dashboard.html', template_context)


@login_required
def modify_event_view(request, event_id):
    # This view is for the edit page/form, not the details panel
    try:
        event_data = {'id': event_id, 'title': 'Fetched Event Title'}
    except Exception:
        messages.error(request, f"Event with ID {event_id} was not found.")
        return redirect('manage_events_root')
    if request.method == 'POST':
        messages.success(request, f"Event '{event_data.get('title', 'Event')}' updated successfully.")
        return redirect('manage_events_root')
    return render(request, 'fragments/manage_event/modify_event_form.html', {'event': event_data})


def manage_events_view(request):
    return render(request, 'fragments/manage_event/manage_events_content.html')