import datetime
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache

from apps.admin_dashboard_page.models import Event
from apps.admin_dashboard_page.models import AdminProfile  # Make sure this import exists


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
    try:
        event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
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
        event_end_dt = None

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

        if not event_end_dt:
            event_end_dt = event_start_dt + datetime.timedelta(hours=1)

        now = datetime.datetime.now()
        if now >= event_end_dt:
            return "Completed"
        elif event_start_dt <= now < event_end_dt:
            return "Active/Started"

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
    # Check if user is actually an admin and verified
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access the admin dashboard.")
        return redirect('student_dashboard')

    try:
        admin_profile = AdminProfile.objects.get(user=request.user)
        if not admin_profile.is_verified:
            messages.error(request, "Please verify your email address to access the dashboard.")
            return redirect('logout')
    except AdminProfile.DoesNotExist:
        messages.error(request, "Admin profile not found. Please contact support.")
        return redirect('logout')

    is_ajax = request.GET.get('is_ajax') == 'true'
    today = datetime.date.today()

    admin_filter_id = admin_profile.id
    cache_key = f"dashboard_data_{admin_filter_id}"
    cached_data = cache.get(cache_key)

    if cached_data:
        context = cached_data
    else:
        total_events = Event.objects.filter(admin_id=admin_filter_id).count()
        upcoming_events_qs = Event.objects.filter(
            admin_id=admin_filter_id,
            date__gte=today
        ).order_by('date')[:50]

        formatted_events = []
        for e in upcoming_events_qs:
            try:
                status = calculate_time_remaining(
                    str(e.date),
                    str(e.start_time),
                    str(e.end_time) if e.end_time else None
                )
                if status == "Completed":
                    continue
                formatted_events.append({
                    'id': e.id,
                    'title': e.title,
                    'start_date': format_to_readable_date(str(e.date)),
                    'start_time': format_to_12hr(str(e.start_time)),
                    'location': e.location,
                    'time_remaining': status
                })
            except Exception:
                continue

        formatted_events = formatted_events[:10]
        context = {
            'admin_organization': admin_profile.organization_name,
            'admin_name': admin_profile.name,
            'total_events': total_events,
            'total_attendance': 0,
            'new_feedback': 0,
            'notification_count': 0,
            'events': formatted_events,
        }
        cache.set(cache_key, context, timeout=60)

    if not request.session.get('welcome_shown', False):
        name = admin_profile.name or request.user.username or "Admin"
        messages.success(request, f"Welcome, {name}!")
        request.session['welcome_shown'] = True

    template = 'fragments/dashboard_content.html' if is_ajax else 'admin_dashboard.html'
    return render(request, template, context)