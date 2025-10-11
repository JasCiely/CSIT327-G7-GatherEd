import datetime
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from supabase import create_client, Client


def logout_view(request):
    logout(request)
    request.session.flush()
    messages.success(request, "You have been logged out.")
    return redirect('index')


def calculate_time_remaining(event_date_str, start_time_str):
    try:
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()

        try:
            start_time = datetime.datetime.strptime(start_time_str, '%H:%M:%S').time()
        except ValueError:
            start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()

        event_start_dt = datetime.datetime.combine(event_date, start_time)
        now = datetime.datetime.now()

        time_diff = event_start_dt - now
        total_seconds = time_diff.total_seconds()

        if total_seconds <= 0:
            return "Active/Started"

        days = time_diff.days
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60

        parts = []

        if total_seconds >= 86400:
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

        elif total_seconds < 86400:
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        if not parts and total_seconds > 0:
            return "Starts in seconds"

        return ", ".join(parts) + " left"

    except Exception:
        return "Time Unknown"


def format_to_12hr(time_str):
    try:
        dt_obj = datetime.datetime.strptime(time_str, '%H:%M:%S')
        return dt_obj.strftime('%I:%M %p').lstrip('0')
    except ValueError:
        try:
            dt_obj = datetime.datetime.strptime(time_str, '%H:%M')
            return dt_obj.strftime('%I:%M %p').lstrip('0')
        except:
            return time_str


def format_to_readable_date(date_str):
    if not date_str:
        return 'N/A'
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        return date_obj.strftime('%B %d, %Y').lstrip('0')
    except Exception:
        return date_str


@login_required
def admin_dashboard(request):
    is_ajax = request.GET.get('is_ajax') == 'true'
    context = {
        'total_events': 0,
        'total_attendance': 0,
        'new_feedback': 0,
        'notification_count': 0,
        'events': [],
        'admin_organization': 'N/A'
    }
    today_date_str = datetime.date.today().isoformat()
    now = datetime.datetime.now()

    try:
        supabase_client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )

        admin_profile = request.user.adminprofile
        admin_filter_id = str(admin_profile.id)
        context['admin_organization'] = admin_profile.organization_name

        total_events_response = (supabase_client.table('events')
                                 .select('id', count='exact')
                                 .eq('admin_id', admin_filter_id)
                                 .limit(0)
                                 .execute())

        upcoming_events_data = (supabase_client.table('events')
                                .select('id, title, date, location, start_time')
                                .eq('admin_id', admin_filter_id)
                                .gte('date', today_date_str)
                                .order('date', desc=False)
                                .limit(50)
                                .execute()).data

        if upcoming_events_data:
             total_events_query = (supabase_client.table('events')
                                   .select('id')
                                   .eq('admin_id', admin_filter_id)
                                   .execute()).data
             context['total_events'] = len(total_events_query) if total_events_query else 0
        else:
            context['total_events'] = 0

        full_events = []
        if upcoming_events_data:
            for event in upcoming_events_data:
                try:
                    try:
                        start_time = datetime.datetime.strptime(event['start_time'], '%H:%M:%S').time()
                    except ValueError:
                        start_time = datetime.datetime.strptime(event['start_time'], '%H:%M').time()

                    event_start_dt = datetime.datetime.combine(
                        datetime.datetime.strptime(event['date'], '%Y-%m-%d').date(),
                        start_time
                    )

                    if now < event_start_dt:
                        full_events.append({
                            'id': event['id'],
                            'title': event['title'],
                            'date': event['date'],
                            'start_time': event['start_time'],
                            'location': event['location'],
                            'event_start_dt': event_start_dt
                        })

                except Exception as e:
                    print(f"Skipping event due to date/time parsing error: {e}")
                    continue

        full_events.sort(key=lambda x: x['event_start_dt'])

        formatted_events = []
        for event in full_events[:10]:
            time_remaining = calculate_time_remaining(event['date'], event['start_time'])

            formatted_events.append({
                'id': event['id'],
                'title': event['title'],
                'start_date': format_to_readable_date(event['date']),
                'start_time': format_to_12hr(event['start_time']),
                'location': event['location'],
                'time_remaining': time_remaining
            })

        context['events'] = formatted_events


    except AttributeError:
        print("ERROR: AdminProfile not found for user.")
        messages.error(request, "Admin profile data is incomplete. Please contact support.")
        return redirect('logout')

    except Exception as e:
        print(f"ERROR: Admin dashboard data fetch failed: {e}")
        messages.error(request, f"Could not load dashboard data. Check database records or RLS rules.")

    if is_ajax:
        return render(request, 'fragments/dashboard_content.html', context)
    else:
        return render(request, 'admin_dashboard.html', context)