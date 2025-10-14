from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
import uuid
import datetime

from apps.register_page.models import AdminProfile

@login_required
def create_event(request):
    is_ajax = request.GET.get('is_ajax') == 'true'

    # Initialize Supabase client
    try:
        supabase_admin: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    except AttributeError:
        messages.error(request, 'Server configuration error: Supabase service key is missing.')
        return redirect('admin_dashboard')

    # Get current admin profile
    try:
        admin_profile = get_object_or_404(AdminProfile, user=request.user)
        current_admin_id = admin_profile.pk
    except Exception:
        messages.error(request, 'Authentication error: Admin profile is missing in the database.')
        return redirect('admin_dashboard')

    # Handle POST request to create new event
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description')
            date = request.POST.get('date')
            location = request.POST.get('location')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            max_attendees = request.POST.get('max_attendees')

            # Required fields check
            if not all([title, description, date, start_time]):
                messages.error(request, "Event title, description, date, and start time are required.")
                return redirect('admin_dashboard')

            # ✅ Check for duplicate event
            existing_event = supabase_admin.table('events') \
                .select('id') \
                .eq('admin_id', current_admin_id) \
                .eq('title', title) \
                .eq('date', date) \
                .eq('start_time', start_time) \
                .eq('end_time', end_time) \
                .eq('location', location) \
                .execute().data

            if existing_event:
                messages.error(request, "An event with the same title, date, time, and location already exists.")
                return redirect('admin_dashboard')

            # Insert new event
            new_uuid = str(uuid.uuid4())
            insert_data = {
                'id': new_uuid,
                'admin_id': current_admin_id,
                'title': title,
                'description': description,
                'date': date,
                'location': location,
                'start_time': start_time,
                'end_time': end_time,
                'max_attendees': int(max_attendees) if max_attendees and max_attendees.isdigit() else None,
                'picture_url': None,
                'created_at': datetime.datetime.now().isoformat(),
            }

            insert_result = supabase_admin.table('events').insert(insert_data).execute()
            if not insert_result.data:
                raise Exception("Failed to insert event into database")

            # Invalidate cache so dashboard updates immediately
            cache_key = f"dashboard_data_{current_admin_id}"
            cache.delete(cache_key)

            messages.success(request, f"Event '{title}' scheduled successfully!")
            response = redirect('admin_dashboard')
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

        except Exception as e:
            messages.error(request, f"Failed to create event: {e}")
            return redirect('admin_dashboard')

    # Render event creation form for GET request (AJAX)
    if is_ajax:
        return render(request, 'fragments/create_event/create_event_content.html')

    # Redirect non-AJAX GET requests
    return redirect('admin_dashboard')
