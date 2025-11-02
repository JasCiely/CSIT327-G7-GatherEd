from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
import uuid
import datetime

from apps.register_page.models import AdminProfile


@login_required
def create_event(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    try:
        supabase_admin: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    except AttributeError:
        msg = "Server configuration error: Supabase service key missing."
        if is_ajax:
            return JsonResponse({"message": msg}, status=500)
        messages.error(request, msg)
        return redirect('admin_dashboard')

    try:
        admin_profile = get_object_or_404(AdminProfile, user=request.user)
        current_admin_id = admin_profile.pk
    except Exception:
        msg = "Authentication error: Admin profile missing."
        if is_ajax:
            return JsonResponse({"message": msg}, status=403)
        messages.error(request, msg)
        return redirect('admin_dashboard')

    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description')
            date = request.POST.get('date')
            location = request.POST.get('location')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            max_attendees = request.POST.get('max_attendees')

            if not all([title, description, date, start_time, end_time, location]):
                msg = "All fields except Max Attendees are required."
                if is_ajax:
                    return JsonResponse({"message": msg}, status=400)
                messages.error(request, msg)
                return redirect('admin_dashboard')

            existing_event = supabase_admin.table('events') \
                .select('*') \
                .eq('admin_id', current_admin_id) \
                .eq('title', title) \
                .eq('date', date) \
                .eq('start_time', start_time) \
                .eq('end_time', end_time) \
                .eq('location', location) \
                .execute()

            if existing_event.data:
                msg = "An identical event already exists."
                if is_ajax:
                    return JsonResponse({"message": msg}, status=409)
                messages.error(request, msg)
                return redirect('admin_dashboard')

            insert_data = {
                'id': str(uuid.uuid4()),
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

            result = supabase_admin.table('events').insert(insert_data).execute()
            if not result.data:
                raise Exception("Database insert failed")

            cache_key = f"dashboard_data_{current_admin_id}"
            cache.delete(cache_key)

            if is_ajax:
                return JsonResponse({"success": True, "redirect_url": "/admin/dashboard/"}, status=200)

            messages.success(request, f"Event '{title}' scheduled successfully!")
            return redirect('admin_dashboard')

        except Exception as e:
            msg = f"Failed to create event: {e}"
            if is_ajax:
                return JsonResponse({"message": msg}, status=500)
            messages.error(request, msg)
            return redirect('admin_dashboard')

    if request.GET.get('is_ajax') == 'true':
        return render(request, 'fragments/create_event/create_event_content.html')

    return redirect('admin_dashboard')
