import datetime
import concurrent.futures
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.cache import cache
from supabase import create_client, Client


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


def calculate_time_remaining(event_date_str, start_time_str, end_time_str=None):
    """
    Returns the status of the event:
    - "Active/Started" if the current time is between start and end time
    - "Completed" if current time is after or at the end time
    - Time remaining if event is in the future
    """
    try:
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()

        # Parse start time
        start_time = None
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                start_time = datetime.datetime.strptime(start_time_str, fmt).time()
                break
            except ValueError:
                continue
        if not start_time:
            return "Time Unknown"

        event_start_dt = datetime.datetime.combine(event_date, start_time)

        # Initialize event_end_dt
        event_end_dt = None

        # Parse end time if provided
        if end_time_str:
            end_time = None
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    end_time = datetime.datetime.strptime(end_time_str, fmt).time()
                    break
                except ValueError:
                    continue

            if end_time:
                event_end_dt = datetime.datetime.combine(event_date, end_time)

        # If no valid end time was parsed, default to 1 hour duration
        if not event_end_dt:
            event_end_dt = event_start_dt + datetime.timedelta(hours=1)

        now = datetime.datetime.now()

        # Priority 1: Check for Completed Status (at or after end time)
        if now >= event_end_dt:
            return "Completed"

        # Priority 2: Check for Active/Started Status (between start and end time)
        elif event_start_dt <= now < event_end_dt:
            return "Active/Started"

        # Remaining time (must be a future event)
        diff = event_start_dt - now
        days = diff.days
        hrs, mins = divmod(diff.seconds, 3600)
        mins //= 60
        if days > 0:
            return f"{days} day{'s' if days != 1 else ''}, {hrs} hr{'s' if hrs != 1 else ''} left"
        if hrs > 0:
            return f"{hrs} hr{'s' if hrs != 1 else ''}, {mins} min{'s' if mins != 1 else ''} left"
        return f"{mins} minute{'s' if mins != 1 else ''} left"

    except Exception:
        return "Time Unknown"


def format_to_12hr(time_str):
    try:
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                dt = datetime.datetime.strptime(time_str, fmt)
                return dt.strftime('%I:%M %p').lstrip('0')
            except ValueError:
                continue
        return time_str
    except Exception:
        return time_str


def format_to_readable_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y').lstrip('0')
    except Exception:
        return date_str


@login_required
def admin_dashboard(request):
    is_ajax = request.GET.get('is_ajax') == 'true'
    today_str = datetime.date.today().isoformat()
    user = request.user

    try:
        admin_profile = user.adminprofile
    except AttributeError:
        messages.error(request, "Admin profile not found. Please contact support.")
        return redirect('logout')

    admin_filter_id = str(admin_profile.id)

    # ⚡ Try pulling cached data first (cache per admin for 1 min)
    cache_key = f"dashboard_data_{admin_filter_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        context = cached_data
    else:
        supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

        def get_total_events():
            data = supabase_client.table('events').select('id').eq('admin_id', admin_filter_id).execute().data
            return len(data) if data else 0

        def get_upcoming_events():
            # Query events starting from today or later (we will filter out completed ones in Python)
            data = (supabase_client.table('events')
                    # Include 'end_time' in the select
                    .select('id, title, date, location, start_time, end_time')
                    .eq('admin_id', admin_filter_id)
                    .gte('date', today_str)
                    .order('date', desc=False)
                    .execute()).data
            return data or []

        # ⚡ Run both queries concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_events = executor.submit(get_total_events)
            future_upcoming = executor.submit(get_upcoming_events)
            total_events = future_events.result()
            upcoming_data = future_upcoming.result()

        formatted_events = []

        for e in upcoming_data:
            try:
                end_time_data = e.get('end_time')

                # Calculate status
                status = calculate_time_remaining(e['date'], e['start_time'], end_time_data)

                # 🛑 FILTER: Skip event if the status is "Completed"
                if status == "Completed":
                    continue

                formatted_events.append({
                    'id': e['id'],
                    'title': e['title'],
                    'start_date': format_to_readable_date(e['date']),
                    'start_time': format_to_12hr(e['start_time']),
                    'location': e['location'],
                    # Use the already calculated status/time remaining
                    'time_remaining': status
                })
            except Exception:
                continue

        formatted_events = formatted_events[:10]

        context = {
            'admin_organization': admin_profile.organization_name,
            'total_events': total_events,
            # Placeholder values for attendance/feedback
            'total_attendance': 0,
            'new_feedback': 0,
            'notification_count': 0,
            'events': formatted_events,
        }

        cache.set(cache_key, context, timeout=60)

    # ✅ Show “Welcome back” message once
    if not request.session.get('welcome_shown', False):
        name = user.first_name or user.username or "Admin"
        messages.success(request, f"Welcome back, {name}!")
        request.session['welcome_shown'] = True

    template = 'fragments/dashboard_content.html' if is_ajax else 'admin_dashboard.html'
    return render(request, template, context)