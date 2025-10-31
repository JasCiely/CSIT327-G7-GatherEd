import datetime
import traceback

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from supabase import create_client
from django.contrib.auth.decorators import login_required
from django.core.cache import cache


# --- HELPER FUNCTIONS ---

def format_to_readable_date(date_str):
    if not date_str:
        return 'N/A'
    try:
        if isinstance(date_str, datetime.date):
            date_obj = date_str
        else:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

        return date_obj.strftime('%B %d, %Y').lstrip('0')
    except Exception:
        return date_str


def format_to_12hr(time_str):
    if isinstance(time_str, datetime.time):
        time_obj = time_str
    else:
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                time_obj = datetime.datetime.strptime(time_str, fmt).time()
                break
            except ValueError:
                continue
        else:
            return time_str

    return time_obj.strftime('%I:%M %p').lstrip('0')


def get_event_status(event_date_str, start_time_str, end_time_str):
    if not all([event_date_str, start_time_str]):
        return 'Unknown'
    try:
        if isinstance(event_date_str, str):
            event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
        else:
            event_date = event_date_str

        def parse_time(ts):
            if isinstance(ts, datetime.time): return ts
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    return datetime.datetime.strptime(ts, fmt).time()
                except ValueError:
                    continue
            return datetime.time(0, 0)

        now = datetime.datetime.now()
        start_dt = datetime.datetime.combine(event_date, parse_time(start_time_str))

        if end_time_str:
            end_dt = datetime.datetime.combine(event_date, parse_time(end_time_str))
        else:
            # Default to 2 hours if end time is missing
            end_dt = start_dt + datetime.timedelta(hours=2)

        if now < start_dt:
            return 'Upcoming'
        elif start_dt <= now <= end_dt:
            return 'Active'
        return 'Completed'
    except Exception:
        return 'Unknown'


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
        return None

    date_str = data.get('date', '')
    start_time_str = data.get('start_time', '')
    end_time_str = data.get('end_time', '')
    event_status = get_event_status(date_str, start_time_str, end_time_str)

    # NOTE: Placeholder for registrations
    current_registrations_count = 0

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

        # Return raw ISO strings for HTML input pre-population
        'raw_date': date_str,
        'raw_start_time': start_time_str,
        'raw_end_time': end_time_str,
    }


# --- CORE VIEWS ---

@login_required
def manage_events(request):
    """Handles Manage Events page."""
    is_ajax = request.GET.get('is_ajax') == 'true'
    admin_id = str(request.user.adminprofile.id)
    cache_key = f"events_{admin_id}"
    events_list = []

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
            'max_attendees': ev.get('max_attendees', 0) or 0,
        } for ev in data]
        cache.set(cache_key, events_list, timeout=60)
    except Exception as e:
        print(f"[Supabase error] {e}")

    context = {'events_list': events_list, 'title': 'Manage Events'}

    if is_ajax:
        return render(request, 'fragments/manage_event/manage_events_content.html', context)

    # Redirect to the main dashboard container page
    return redirect('/admin_dashboard/')


@login_required
def get_event_details_html(request, event_id):
    """AJAX endpoint to fetch and render the event details fragment."""
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return HttpResponse("Unauthorized", status=403)

    try:
        admin_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

        event_data = _fetch_single_event(event_id, admin_client)

        if not event_data:
            return HttpResponse(
                '<div style="color: red; padding: 20px;">Error 404: Event not found.</div>',
                status=404)

        return render(request, 'fragments/manage_event/event_details_fragment.html', {'event': event_data})

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"CRITICAL ERROR in get_event_details_html: {e}\n{error_trace}")
        return HttpResponse(
            '<div style="color: red; padding: 20px;">Error 500: Server failed to load details.</div>',
            status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_event(request, event_id):
    """Deletes an event from Supabase."""
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Unauthorized: Not an AJAX request'}, status=403)

    admin_id = str(request.user.adminprofile.id)

    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        # Security check: Ensure the event belongs to the current admin
        fetch_result = client.table('events').select('id').eq('id', event_id).eq('admin_id', admin_id).execute()

        if not getattr(fetch_result, 'data', []):
            return JsonResponse({'success': False, 'error': 'Event not found or unauthorized to delete.'}, status=404)

        client.table('events').delete().eq('id', event_id).execute()
        cache.delete(f"events_{admin_id}")

        return JsonResponse({'success': True})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def modify_event_root(request, event_id):
    """
    Handles GET (AJAX) to render the edit form with current data,
    and POST (AJAX) to update the event details via Supabase.
    """
    is_ajax = request.GET.get('is_ajax') == 'true'
    admin_id = str(request.user.adminprofile.id)

    if not is_ajax:
        return JsonResponse({'error': 'Invalid request: Must be an AJAX call.'}, status=400)

    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        # 1. Fetch Event Data (Security: ensure it belongs to the current admin)
        event_query = client.table('events') \
            .select('*') \
            .eq('id', event_id) \
            .eq('admin_id', admin_id) \
            .single() \
            .execute()

        event_data = getattr(event_query, 'data', None)

        if not event_data:
            return JsonResponse({'success': False, 'error': 'Event not found or unauthorized.'}, status=404)

    except Exception:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': 'Database connection error.'}, status=500)

    # --- HANDLE POST (AJAX Submission for Update) ---
    if request.method == 'POST':
        try:
            update_data = {
                'title': request.POST.get('title'),
                'description': request.POST.get('description'),
                'date': request.POST.get('date'),
                'start_time': request.POST.get('start_time'),
                'end_time': request.POST.get('end_time') if request.POST.get('end_time') else None,
                'location': request.POST.get('location'),
                'max_attendees': int(request.POST.get('max_attendees')) if request.POST.get('max_attendees') else 0,
            }

            client.table('events') \
                .update(update_data) \
                .eq('id', event_id) \
                .execute()

            cache.delete(f"events_{admin_id}")

            # Re-fetch the updated data for client-side table row refresh
            updated_event_query = client.table('events').select('*').eq('id', event_id).single().execute()
            updated_event = getattr(updated_event_query, 'data', None)

            return JsonResponse({
                'success': True,
                'message': f'Event "{update_data["title"]}" updated successfully.',
                'updated_data': {
                    'id': event_id,
                    'name': updated_event['title'],
                    'date': format_to_readable_date(updated_event['date']),
                    'registrations': 0,
                    'status': get_event_status(updated_event['date'], updated_event['start_time'],
                                               updated_event['end_time']),
                }
            })

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f'Update failed: {str(e)}'}, status=400)


    # --- HANDLE GET (AJAX Request to Render Form Fragment) ---
    elif request.method == 'GET':
        context = {
            'event': event_data,
            'current_date': event_data.get('date', ''),
            'current_start_time': event_data.get('start_time', ''),
            'current_end_time': event_data.get('end_time', ''),
        }

        html_content = render_to_string(
            'fragments/manage_event/modify_event_form.html',
            context,
            request=request
        )

        # The fix: Return the HTML content inside a JSON object.
        return JsonResponse({'success': True, 'html': html_content})

    return JsonResponse({'error': 'Method not allowed'}, status=405)