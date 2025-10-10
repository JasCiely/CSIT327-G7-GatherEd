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
    # Assuming 'index' is the correct URL name for the homepage
    return redirect('index')

@login_required
def admin_dashboard(request):
    is_ajax = request.GET.get('is_ajax') == 'true'
    context = {}
    today_date_str = datetime.date.today().isoformat() # Get today's date in YYYY-MM-DD format

    try:
        # NOTE: Using SUPABASE_SERVICE_ROLE_KEY is generally better for filtering
        # on secure columns like 'admin_id' for RLS purposes, but sticking to
        # ANON_KEY here as per your original file structure.
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

        # --- Upcoming Events List (REAL DATA) ---
        # 💡 CHANGE: Filter where 'date' is Greater Than (gt) today's date.
        upcoming_events = (supabase_client.table('events')
                           .select('id, title, date, location, start_time')
                           .eq('admin_id', admin_filter_id)
                           .gt('date', today_date_str) # Filter: Date > Today
                           .order('date', desc=False)
                           .limit(5) # Limit to 5 for dashboard snippet
                           .execute()).data

        # 💡 FIX: Adapt the Supabase keys ('date' -> 'start_date') to match the HTML template
        # The HTML template uses: 'title', 'start_date', 'start_time', 'location'
        formatted_events = []
        if upcoming_events:
            for event in upcoming_events:
                formatted_events.append({
                    'id': event['id'],
                    'title': event['title'],
                    'start_date': event['date'],       # Map 'date' (DB) to 'start_date' (HTML)
                    'start_time': event['start_time'], # Keep 'start_time'
                    'location': event['location'],
                })

        context = {
            'admin_organization': admin_profile.organization_name,
            'total_events': total_events,
            'total_attendance': 0,
            'new_feedback': 0,
            'notification_count': 0,
            # Pass the correctly filtered and formatted list
            'events': formatted_events,
        }

    except AttributeError:
        # ... (error handling remains the same)
        print("ERROR: AdminProfile not found for user.")
        messages.error(request, "Admin profile data is incomplete. Please contact support.")
        return redirect('logout')
    except Exception as e:
        # ... (error handling remains the same)
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