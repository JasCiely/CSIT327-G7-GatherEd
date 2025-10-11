import datetime
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from supabase import create_client, Client
from django.contrib import messages


def logout_view(request):
    logout(request)
    request.session.flush()
    request.session.clear_expired()
    messages.success(request, "You have been logged out.")
    response = redirect('index')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def calculate_time_remaining(event_date_str, start_time_str):
    """
    Calculates the time difference and formats it:
    - If > 24 hours: Show Days and Hours.
    - If < 24 hours: Show Hours and Minutes.
    """
    try:
        # Combine date and time into a single datetime object
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()

        # Robustly parse time
        try:
            start_time = datetime.datetime.strptime(start_time_str, '%H:%M:%S').time()
        except ValueError:
            start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()

        event_start_dt = datetime.datetime.combine(event_date, start_time)
        now = datetime.datetime.now()

        # Calculate the difference
        time_diff = event_start_dt - now
        total_seconds = time_diff.total_seconds()

        if total_seconds <= 0:
            return "Active/Started"

        days = time_diff.days
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60

        parts = []

        if total_seconds >= 86400:  # 24 hours or more
            # Display Days and Hours
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

        elif total_seconds < 86400:  # Less than 24 hours
            # Display Hours and Minutes
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

            # Always show minutes if it's less than 24 hours away
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        if not parts and total_seconds > 0:
            return "Starts in seconds"

        return ", ".join(parts) + " left"

    except Exception:
        return "Time Unknown"


def format_to_12hr(time_str):
    """Converts a 24-hour time string (HH:MM:SS or HH:MM) to 12-hour format (H:MM AM/PM)."""
    try:
        dt_obj = datetime.datetime.strptime(time_str, '%H:%M:%S')
        return dt_obj.strftime('%I:%M %p').lstrip('0')
    except ValueError:
        try:
            dt_obj = datetime.datetime.strptime(time_str, '%H:%M')
            return dt_obj.strftime('%I:%M %p').lstrip('0')
        except:
            return time_str  # Return original if parsing fails


def format_to_readable_date(date_str):
    """Converts a date string (YYYY-MM-DD) to a readable format (Month Day, Year)."""
    if not date_str:
        return 'N/A'
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        # Example output: October 10, 2025
        return date_obj.strftime('%B %d, %Y').lstrip('0')
    except Exception:
        return date_str


@login_required
def admin_dashboard(request):
    is_ajax = request.GET.get('is_ajax') == 'true'
    context = {}
    today_date_str = datetime.date.today().isoformat()

    try:
        supabase_client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )

        admin_profile = request.user.adminprofile
        admin_filter_id = str(admin_profile.id)

        # --- Total Events Managed ---
        events_data = (supabase_client.table('events')
                       .select('id')
                       .eq('admin_id', admin_filter_id)
                       .execute()).data

        total_events = len(events_data) if events_data else 0

        # --- Upcoming Events List ---
        upcoming_events_data = (supabase_client.table('events')
                                .select('id, title, date, location, start_time')
                                .eq('admin_id', admin_filter_id)
                                .gte('date', today_date_str)
                                .order('date', desc=False)
                                .execute()).data

        # --- Processing and Formatting Events ---
        formatted_events = []
        now = datetime.datetime.now()

        if upcoming_events_data:
            full_events = []
            for event in upcoming_events_data:
                try:
                    # Robustly parse time
                    try:
                        start_time = datetime.datetime.strptime(event['start_time'], '%H:%M:%S').time()
                    except ValueError:
                        start_time = datetime.datetime.strptime(event['start_time'], '%H:%M').time()

                    event_start_dt = datetime.datetime.combine(
                        datetime.datetime.strptime(event['date'], '%Y-%m-%d').date(),
                        start_time
                    )

                    # Only include events that haven't started yet
                    if now < event_start_dt:
                        full_events.append({
                            **event,
                            'event_start_dt': event_start_dt
                        })

                except Exception as e:
                    print(f"Skipping event due to date/time parsing error: {e}")
                    continue

            # Sort the truly upcoming events by their full datetime object
            full_events.sort(key=lambda x: x['event_start_dt'])

            # Format the final list
            for event in full_events[:10]:  # Limiting to 10 for dashboard display efficiency
                time_remaining = calculate_time_remaining(event['date'], event['start_time'])

                formatted_events.append({
                    'id': event['id'],
                    'title': event['title'],
                    'start_date': format_to_readable_date(event['date']),  # Apply new readable date format
                    'start_time': format_to_12hr(event['start_time']),
                    'location': event['location'],
                    'time_remaining': time_remaining
                })

        context = {
            'admin_organization': admin_profile.organization_name,
            'total_events': total_events,
            'total_attendance': 0,
            'new_feedback': 0,
            'notification_count': 0,
            'events': formatted_events,
        }

    except AttributeError:
        print("ERROR: AdminProfile not found for user.")
        messages.error(request, "Admin profile data is incomplete. Please contact support.")
        return redirect('logout')
    except Exception as e:
        print(f"ERROR: Admin dashboard data fetch failed: {e}")
        messages.error(request, f"Could not load dashboard data. Check database records or RLS rules.")
        context = {
            'total_events': 0,
            'total_attendance': 0,
            'new_feedback': 0,
            'notification_count': 0,
            'events': [],
        }

    if is_ajax:
        return render(request, 'fragments/dashboard_content.html', context)
    else:
        return render(request, 'admin_dashboard.html', context)