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
    if not time_str:
        return ''
    try:
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
    except Exception:
        return time_str


def parse_time(ts):
    if isinstance(ts, datetime.time):
        return ts
    if not ts:
        return datetime.time(0, 0)
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            return datetime.datetime.strptime(ts, fmt).time()
        except ValueError:
            continue
    return datetime.time(0, 0)


def get_detailed_event_timing(event_date_str, start_time_str, end_time_str, manual_close_date_str=None,
                              manual_close_time_str=None):
    """
    Returns a dictionary of critical datetime objects and the event's life status.
    Event Life Status: Upcoming, Active, Completed
    """
    try:
        if not all([event_date_str, start_time_str]):
            return {'status': 'Unknown'}

        # 1. Core Event Times
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
        start_time = parse_time(start_time_str)
        # Default end time to 2 hours after start if not provided
        default_end_dt = datetime.datetime.combine(event_date, start_time) + datetime.timedelta(hours=2)
        end_time = parse_time(end_time_str) if end_time_str else default_end_dt.time()

        start_dt = datetime.datetime.combine(event_date, start_time)
        end_dt = datetime.datetime.combine(event_date, end_time)

        # Handle end_dt before start_dt (e.g., event spans midnight)
        if end_dt < start_dt:
            end_dt += datetime.timedelta(days=1)

        # 2. Manual Limit Time
        manual_limit_dt = None
        if manual_close_date_str and manual_close_time_str:
            limit_date = datetime.datetime.strptime(manual_close_date_str, '%Y-%m-%d').date()
            limit_time = parse_time(manual_close_time_str)
            manual_limit_dt = datetime.datetime.combine(limit_date, limit_time)

        # 3. Event Life Status
        now = datetime.datetime.now()
        status = 'Upcoming'
        if now >= end_dt:
            status = 'Completed'
        elif now >= start_dt:
            status = 'Active'

        return {
            'status': status,
            'start_dt': start_dt,
            'end_dt': end_dt,
            'manual_limit_dt': manual_limit_dt,
            'event_date_str': event_date_str,
            'event_date': event_date,
        }

    except Exception:
        traceback.print_exc()
        return {'status': 'Unknown'}


def get_event_status(event_date_str, start_time_str, end_time_str):
    """Return Upcoming, Active, Completed (Simplified wrapper)"""
    return get_detailed_event_timing(event_date_str, start_time_str, end_time_str).get('status', 'Unknown')


def determine_registration_status(event_data):
    """
    Determines the final, effective registration status based on event data,
    timing, and manual overrides.
    """
    manual = (event_data.get('manual_status_override') or 'AUTO').upper()
    max_attendees = event_data.get('max_attendees') or 0
    current_regs = event_data.get('current_registrations', 0)

    timing = get_detailed_event_timing(
        event_data.get('date'),
        event_data.get('start_time'),
        event_data.get('end_time'),
        event_data.get('manual_close_date'),
        event_data.get('manual_close_time')
    )
    event_status = timing['status']
    now = datetime.datetime.now()

    # --- 1. Manual Overrides (with time limits) ---
    if manual in ['OPEN_MANUAL', 'CLOSED_MANUAL']:
        limit_dt = timing.get('manual_limit_dt')

        # Check if manual override has expired (Manual override ends AT the limit time)
        if limit_dt and now >= limit_dt:
            # Revert to AUTO logic after limit expires
            manual = 'AUTO'
        else:
            # Manual override is active
            if manual == 'OPEN_MANUAL':
                return 'Available'
            if manual == 'CLOSED_MANUAL':
                return 'Registration Closed'

    # --- 2. Hard Overrides (FULL, ONGOING) ---
    if manual == 'FULL':
        return 'Full'
    if manual == 'ONGOING':
        return 'Closed – Event Ongoing'

    # --- 3. AUTO Logic based on Event Life Status and Capacity ---

    # 3.1 Completed Events (REGISTRATION CLOSED)
    if event_status == 'Completed':
        return 'Registration Closed'

    # 3.2 Active Events (Running)
    if event_status == 'Active':
        # AUTO logic for active event defaults to 'Closed – Event Ongoing' unless maxed
        if max_attendees and current_regs >= max_attendees:
            return 'Full'
        else:
            return 'Closed – Event Ongoing'

            # 3.3 Upcoming Events (or Unknown fallback)
    if max_attendees and current_regs >= max_attendees:
        return 'Full'

    return 'Available'


def fetch_single_event(event_id, admin_client):
    """Return full event dict with formatted values"""
    try:
        res = admin_client.table('events') \
            .select('*') \
            .eq('id', event_id) \
            .single() \
            .execute()
        data = getattr(res, 'data', None)
        if not data:
            return None

        # Placeholder for current registrations
        current_regs = data.get('current_registrations', 0)

        return {
            'id': data['id'],
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'location': data.get('location', ''),
            'date': data.get('date', ''),
            'start_time': data.get('start_time', ''),
            'end_time': data.get('end_time', ''),
            'max_attendees': data.get('max_attendees', 0) or 0,
            'manual_status_override': data.get('manual_status_override', 'AUTO'),
            # Include both date and time fields
            'manual_close_date': data.get('manual_close_date', ''),
            'manual_close_time': data.get('manual_close_time', ''),
            'current_registrations': current_regs,
        }
    except Exception:
        traceback.print_exc()
        return None


def _fetch_single_event(event_id, admin_client):
    """Fetches full details for one event and formats the data."""
    try:
        fetch_result = admin_client.table('events') \
            .select('*') \
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

    current_registrations_count = data.get('current_registrations', 0)
    registration_status = determine_registration_status(data)
    event_status = get_event_status(date_str, start_time_str, end_time_str)  # Need this for HTML

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
        'status': registration_status,

        # Return raw ISO strings for HTML input pre-population
        'raw_date': date_str,
        'raw_start_time': start_time_str,
        'raw_end_time': end_time_str,
        'event_status': event_status,  # Pass event status for HTML disabling
    }


def get_registration_status(event_data):
    """Alias for consistency."""
    return determine_registration_status(event_data)


# --- CORE VIEWS ---

@login_required
def manage_events(request):
    """Handles Manage Events page with both Event and Registration Status."""
    is_ajax = request.GET.get('is_ajax') == 'true'
    admin_id = str(request.user.adminprofile.id)
    cache_key = f"events_{admin_id}"
    events_list = []

    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        res = client.table('events').select('*').eq('admin_id', admin_id).order('date').execute()
        data = getattr(res, 'data', []) or []

        for ev in data:
            # Event Status
            event_status = get_event_status(ev.get('date'), ev.get('start_time'), ev.get('end_time'))

            # Registration Status Logic - using the comprehensive function
            registration_status = determine_registration_status(ev)

            max_attendees = ev.get('max_attendees', 0) or 0
            current_registrations = ev.get('current_registrations', 0) or 0  # placeholder

            events_list.append({
                'id': ev['id'],
                'name': ev.get('title', 'N/A'),
                'description': ev.get('description', 'N/A'),
                'date': format_to_readable_date(ev.get('date')),
                'location': ev.get('location', 'N/A'),
                'start_time': format_to_12hr(ev.get('start_time')),
                'end_time': format_to_12hr(ev.get('end_time')),
                'event_status': event_status,
                'registration_status': registration_status,
                'registrations': current_registrations,
                'max_attendees': max_attendees,
            })

        cache.set(cache_key, events_list, timeout=60)

    except Exception as e:
        print(f"[Supabase error] {e}")

    context = {'events_list': events_list, 'title': 'Manage Events'}

    if is_ajax:
        return render(request, 'fragments/manage_event/manage_events_content.html', context)

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
    Handles GET to fetch edit form HTML and POST to save event updates via AJAX,
    with server-side validation for manual registration overrides.
    """
    if request.GET.get('is_ajax') != 'true':
        return JsonResponse({'error': 'Must be AJAX'}, status=400)

    admin_id = str(request.user.adminprofile.id)
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    # Fetch the event and current registrations
    event_data = fetch_single_event(event_id, client)

    if not event_data:
        return JsonResponse({'success': False, 'error': 'Event not found or unauthorized'}, status=404)

    # Pre-calculate event life status (needed for both validation and GET context)
    timing = get_detailed_event_timing(
        event_data.get('date'), event_data.get('start_time'), event_data.get('end_time'),
        event_data.get('manual_close_date'), event_data.get('manual_close_time')
    )
    event_life_status = timing['status']

    # --- POST: SAVE EVENT UPDATES AND VALIDATE REGISTRATION LOGIC ---
    if request.method == 'POST':
        # 1. Prepare Data
        manual_status = (request.POST.get('manual_status_override') or 'AUTO').upper()
        manual_close_date = request.POST.get('manual_close_date') or None
        manual_close_time = request.POST.get('manual_close_time') or None

        # Ensure that if status is AUTO or ONGOING, we clear the manual limit fields
        if manual_status in ['AUTO', 'ONGOING']:
            manual_close_date = None
            manual_close_time = None

        update_data = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description'),
            'location': request.POST.get('location'),
            'date': request.POST.get('date'),
            'start_time': request.POST.get('start_time'),
            'end_time': request.POST.get('end_time') or None,
            'max_attendees': int(request.POST.get('max_attendees') or 0),
            'manual_status_override': manual_status,
            'manual_close_date': manual_close_date,
            'manual_close_time': manual_close_time,
        }

        # Re-run timing with post data, as date/time might have changed
        timing_post = get_detailed_event_timing(
            update_data['date'], update_data['start_time'], update_data['end_time'],
            manual_close_date, manual_close_time
        )
        event_life_status_post = timing_post['status']
        manual_limit_dt = timing_post.get('manual_limit_dt')

        # 3. CRITICAL VALIDATION

        # Rule 4: Prevent status change if the event is Completed
        if event_life_status_post == 'Completed' and manual_status != event_data.get('manual_status_override'):
            # Allow changing to AUTO if it was previously set manually, but block all manual sets.
            if manual_status not in ['AUTO']:
                return JsonResponse(
                    {'success': False, 'error': "Cannot manually override registration status for a completed event."},
                    status=400)

        # Rule 5: Cannot set max attendees to less than current registrations
        current_regs = event_data.get('current_registrations', 0)
        if update_data['max_attendees'] != 0 and update_data['max_attendees'] < current_regs:
            return JsonResponse({'success': False,
                                 'error': f"Max attendees ({update_data['max_attendees']}) cannot be less than current registrations ({current_regs})."},
                                status=400)

        # Rules 2 & 3: Validate Manual Override Limit Time
        if manual_status in ['OPEN_MANUAL', 'CLOSED_MANUAL']:
            validation_error = None

            if manual_limit_dt:

                # General validation: Limit cannot be after the event ends
                if manual_limit_dt > timing_post['end_dt']:
                    validation_error = "The manual override limit cannot be set after the event has ended."

                # Rule 2: Upcoming Event Validation (Manual Close)
                elif event_life_status_post == 'Upcoming' and manual_status == 'CLOSED_MANUAL':
                    # Closing date/time must be before the event starts.
                    if manual_limit_dt >= timing_post['start_dt']:
                        validation_error = "Closing limit must be before the event starts."

                # Rule 3: Active Event Validation (Manual Open)
                elif event_life_status_post == 'Active' and manual_status == 'OPEN_MANUAL':
                    # Closing date must be the same as the event date
                    if manual_limit_dt.date() != timing_post['event_date']:
                        validation_error = "Reopening limit date must be the same as the event date."
                    # Time must be during the event duration (after start time and on or before end time)
                    elif not (manual_limit_dt > timing_post['start_dt'] and manual_limit_dt <= timing_post['end_dt']):
                        validation_error = "Reopening limit time must be during the event duration (after start, on or before end)."

            if validation_error:
                return JsonResponse({'success': False, 'error': f"Validation Error: {validation_error}"}, status=400)

        # 4. Save to Supabase and Invalidate Cache
        try:
            client.table('events').update(update_data).eq('id', event_id).execute()
            cache.delete(f"events_{admin_id}")  # Invalidate cache on successful save
            event_data.update(update_data)  # Use updated data for final status calculation

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f"Failed to save changes: {str(e)}"}, status=500)

        # 5. Compute and Return Final Status
        event_data['current_registrations'] = event_data.get('current_registrations', 0)
        event_data['manual_close_date'] = manual_close_date
        event_data['manual_close_time'] = manual_close_time

        final_registration_status = determine_registration_status(event_data)
        final_event_status = get_event_status(update_data['date'], update_data['start_time'], update_data['end_time'])

        return JsonResponse({
            'success': True,
            'updated_data': {
                'id': event_id,
                'name': update_data['title'],
                'date': format_to_readable_date(update_data['date']),
                'status': final_registration_status,
                'event_status': final_event_status,
                'registrations': event_data.get('current_registrations', 0),
            }
        })

    # --- GET: RETURN EDIT FORM HTML ---
    # Fetch event data again to ensure all fields are fresh for the form
    event_data_context = fetch_single_event(event_id, client)

    # Pass event status to the template to disable controls if completed
    event_life_status_context = get_event_status(
        event_data_context.get('date'), event_data_context.get('start_time'), event_data_context.get('end_time')
    )

    context = {
        'event': event_data_context,
        'current_date': event_data_context.get('date', ''),
        'current_start_time': event_data_context.get('start_time', ''),
        'current_end_time': event_data_context.get('end_time', ''),
        'current_manual_close_date': event_data_context.get('manual_close_date', ''),
        'current_manual_close_time': event_data_context.get('manual_close_time', ''),
        'is_completed': event_life_status_context == 'Completed',  # CRITICAL: Flag for HTML
    }
    html_content = render_to_string('fragments/manage_event/modify_event_form.html', context, request=request)
    return JsonResponse({'success': True, 'html': html_content})