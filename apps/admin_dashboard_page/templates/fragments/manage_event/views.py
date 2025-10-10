import datetime
from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def get_event_status(event_date_str, start_time_str, end_time_str):
    """
    Determines the status of an event based on its date and time range.
    """
    if not all([event_date_str, start_time_str, end_time_str]):
        return 'Unknown'

    try:
        # 1. Parse Event Date
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()

        # 2. Parse Start and End Times (robust to different time formats)
        def parse_time(time_str):
            # Try to parse with seconds first, then without
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    return datetime.datetime.strptime(time_str, fmt).time()
                except ValueError:
                    continue
            raise ValueError(f"Time string '{time_str}' does not match expected formats.")

        start_time = parse_time(start_time_str)
        end_time = parse_time(end_time_str)

        # 3. Create full datetime objects for comparison
        event_start_dt = datetime.datetime.combine(event_date, start_time)
        event_end_dt = datetime.datetime.combine(event_date, end_time)

        # Use datetime.datetime.now() for the current moment comparison
        now = datetime.datetime.now()

        # 4. Determine Status
        if now < event_start_dt:
            # Time hasn't come yet
            return 'Upcoming'
        elif event_start_dt <= now <= event_end_dt:
            # Within the scheduled start and end time range
            return 'Active'
        elif now > event_end_dt:
            # The event end time has passed
            return 'Completed'

        # Fallback for unexpected cases
        return 'Unknown'

    except Exception as e:
        # Catch parsing or other errors
        print(f"Error determining event status for {event_date_str}: {e}")
        return 'Unknown'


@login_required
def manage_events(request):
    events_list = []
    is_ajax = request.GET.get('is_ajax', False)

    # 1. Initialize template_context before the try block
    template_context = {
        'events_list': events_list,
        'title': 'Manage Events',
    }

    try:
        # 2. Get the current admin's ID (UUID)
        current_admin_id = request.user.adminprofile.id

        # 🚨 DEBUG: Confirm the ID being used
        print(f"DEBUG: Filtering events for Admin ID (UUID): {current_admin_id}")

        admin_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

        # 3. Fetch events from Supabase filtered by the admin_id
        fetch_result = admin_client.table('events') \
            .select('*') \
            .eq('admin_id', str(current_admin_id)) \
            .order('date', desc=False) \
            .execute()

        # Supabase API Response Error Handling
        if hasattr(fetch_result, 'error') and fetch_result.error:
            error_msg = fetch_result.error.get('message', 'Unknown Supabase error')
            raise Exception(f"Supabase Client Error: {error_msg}")

        data = getattr(fetch_result, 'data', [])
        if data is None:
            data = []

        for event in data:
            # Determine event status based on current time
            event_status = get_event_status(
                event.get('date', ''),
                event.get('start_time', ''),
                event.get('end_time', '')
            )

            # 🛑 PLACEHOLDER FOR REGISTRATION COUNT 🛑
            # Future Code: Fetch the actual count from a 'registrations' table
            # where event_id matches event['id']. For now, initialize to 0.
            current_registrations_count = 0

            events_list.append({
                'id': event['id'],
                'name': event.get('title', 'N/A'),
                'description': event.get('description', 'N/A'),
                'date': event.get('date', 'N/A'),
                'location': event.get('location', 'N/A'),
                'start_time': event.get('start_time', 'N/A'),
                'end_time': event.get('end_time', 'N/A'),
                'max_attendees': event.get('max_attendees', 0),
                'registrations': current_registrations_count,  # Use the placeholder
                'status': event_status,
            })

        # Update the context with the fetched list
        template_context['events_list'] = events_list

    except Exception as e:
        print(f"Error fetching events from Supabase: {e}")
        messages.error(request,
                       "Failed to load events due to a critical server error. Check the Django console for details.")

    if is_ajax:
        return render(request, 'fragments/manage_event/manage_events_content.html', template_context)

    # Template Path: admin_portal/admin_dashboard.html (or wherever it lives)
    return render(request, 'admin_dashboard.html', template_context)


@login_required
def modify_event_view(request, event_id):
    # NOTE: You will need to implement the fetch logic here to get a specific event.
    # e.g., admin_client.table('events').select('*').eq('id', event_id).single().execute()

    try:
        # Placeholder for fetched event data
        event_data = {'id': event_id, 'title': 'Fetched Event Title'}

    except Exception:
        # Handle case where the event ID is invalid or not found
        messages.error(request, f"Event with ID {event_id} was not found.")
        return redirect('manage_events_root')  # Assuming 'manage_events_root' is your list view name

    if request.method == 'POST':
        # Handle event update logic (update Supabase/DB)
        # ...
        messages.success(request, f"Event '{event_data.get('title', 'Event')}' updated successfully.")
        return redirect('manage_events_root')  # Change to your actual root URL name

    # Renders the modification form/view for a specific event
    return render(request, 'fragments/manage_event/modify_event_form.html', {'event': event_data})


def manage_events_view(request):
    # This is a placeholder/wrapper view, its utility depends on your URL configuration.
    return render(request, 'fragments/manage_event/manage_events_content.html')