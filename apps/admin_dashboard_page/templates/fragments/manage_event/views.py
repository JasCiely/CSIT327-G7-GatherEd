import datetime
from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache


def format_to_readable_date(date_str):
    if not date_str:
        return 'N/A'
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y').lstrip('0')
    except Exception:
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
    except Exception:
        return 'Unknown'


@login_required
def manage_events(request):
    """
    Handles Manage Events page.
    Behavior:
    - Normal click (AJAX) => returns fragment only.
    - Full reload / refresh (F5 / Ctrl+R) => redirect to full dashboard with fresh data.
    """
    is_ajax = request.GET.get('is_ajax') == 'true'

    admin_id = str(request.user.adminprofile.id)
    cache_key = f"events_{admin_id}"

    # Always fetch fresh data (no matter what) to ensure correctness on reload
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        res = client.table('events').select('*').eq('admin_id', admin_id).order('date').execute()
        data = getattr(res, 'data', []) or []
        events_list = [{
            'id': ev['id'],
            'name': ev.get('title', 'N/A'),
            'description': ev.get('description', 'N/A'),
            'date': format_to_readable_date(ev.get('date')),
            'location': ev.get('location', 'N/A'),
            'start_time': format_to_12hr(ev.get('start_time')),
            'end_time': format_to_12hr(ev.get('end_time')),
            'status': get_event_status(ev.get('date'), ev.get('start_time'), ev.get('end_time')),
            'registrations': 0,
            'max_attendees': ev.get('max_attendees', 0),
        } for ev in data]
        cache.set(cache_key, events_list, timeout=60)
    except Exception as e:
        print(f"[Supabase error] {e}")
        events_list = []

    context = {'events_list': events_list, 'title': 'Manage Events'}

    # ✅ AJAX load for fragment click (no full page refresh)
    if is_ajax:
        return render(request, 'fragments/manage_event/manage_events_content.html', context)

    # ✅ Full reload (refresh, direct access, F5) => render full dashboard
    return redirect('/admin_dashboard/')



@login_required
def modify_event_view(request, event_id):
    """Edit event details (simplified)."""
    if request.method == 'POST':
        messages.success(request, "Event updated successfully.")
        cache_key = f"manage_events_{request.user.adminprofile.id}"
        cache.delete(cache_key)
        cache.delete(f"{cache_key}_refresh")
        return redirect('manage_event')

    return render(request, 'fragments/manage_event/modify_event_form.html', {'event_id': event_id})

@login_required
def event_details_view(request, event_id):
    """Return event details as a fragment for AJAX requests."""
    try:
        admin_id = str(request.user.adminprofile.id)
        cache_key = f"events_{admin_id}"
        events_list = cache.get(cache_key, [])

        # Find event by ID
        event = next((ev for ev in events_list if str(ev['id']) == str(event_id)), None)
        if not event:
            return render(request, 'fragments/manage_event/error_message.html', {'message': 'Event not found'})

        return render(request, 'fragments/manage_event/event_details_content.html', {'event': event})
    except Exception as e:
        print(f"[Error fetching event details] {e}")
        return render(request, 'fragments/manage_event/error_message.html', {'message': 'Failed to load event details'})

