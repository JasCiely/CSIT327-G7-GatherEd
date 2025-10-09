import datetime
from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def get_event_status(event_date_str):
    """Determines the status of an event based on its date."""
    try:
        # Assuming event_date_str is in 'YYYY-MM-DD' format
        # Use datetime.datetime.strptime from the imported module
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
        today = datetime.date.today()

        if event_date < today:
            return 'Completed'
        elif event_date == today:
            return 'Active'
        else:
            return 'Upcoming'
    except:
        return 'Unknown'

@login_required
def manage_events(request):
    events_list = []
    is_ajax = request.GET.get('is_ajax', False)

    try:
        admin_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

        fetch_result = admin_client.table('events').select('*').order('date', desc=False).execute()

        if not hasattr(fetch_result, 'data') or (hasattr(fetch_result, 'error') and fetch_result.error):
            error_msg = getattr(fetch_result, 'error', {}).get('message', 'Unknown Supabase error')
            raise Exception(f"Supabase Client Error: {error_msg}")

        for event in fetch_result.data:
            mock_registrations = 10

            event_status = get_event_status(event.get('date', ''))

            events_list.append({
                'id': event['id'],
                'name': event.get('title', 'N/A'),
                'description': event.get('description', 'N/A'),
                'date': event.get('date', 'N/A'),
                'location': event.get('location', 'N/A'),
                'start_time': event.get('start_time', 'N/A'),
                'end_time': event.get('end_time', 'N/A'),
                'max_attendees': event.get('max_attendees', 0),
                'registrations': mock_registrations,
                'status': event_status,
            })

    except Exception as e:
        print(f"Error fetching events from Supabase: {e}")
        messages.error(request,
                       "Failed to load events due to a critical server error. Check the Django console for details.")

    template_context = {
        'events_list': events_list,
        'title': 'Manage Events',
    }

    if is_ajax:
        return render(request, 'fragments/manage_event/manage_events_content.html', template_context)

    # Template Path: admin_portal/admin_dashboard.html
    return render(request, 'admin_dashboard.html', template_context)


@login_required
def modify_event_view(request, event_id):

    try:
        event_data = {'id': event_id, 'title': 'Fetched Event Title'}

    except Exception:
        # Handle case where the event ID is invalid
        return render(request, 'error_page.html', {'message': 'Event not found.'})

    if request.method == 'POST':
        # Handle event update logic (update Supabase/DB)
        # ...
        return redirect('manage_events_root')

    return render(request, 'fragments/manage_event/manage_events_content.html', {'event': event_data})


def manage_events_view(request):
    # This is the view for the main management page (if you have one)
    return render(request, 'fragments/manage_event/manage_events_content.html')
