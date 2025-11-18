from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
import uuid

from apps.register_page.models import AdminProfile
from apps.admin_dashboard_page.models import Event


@login_required
def create_event(request):
    is_ajax = request.GET.get('is_ajax') == 'true'
    admin_profile = get_object_or_404(AdminProfile, user=request.user)
    current_admin_id = admin_profile.pk

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        date = request.POST.get('date')
        location = request.POST.get('location')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        max_attendees = request.POST.get('max_attendees')

        if not all([title, description, date, start_time, end_time, location]):
            messages.error(request, "Event title, description, date, start time, end time, and location are required.")
            return redirect('admin_dashboard')

        existing_event = Event.objects.filter(
            admin_id=current_admin_id,
            title=title,
            date=date,
            start_time=start_time,
            end_time=end_time,
            location=location
        ).exists()

        if existing_event:
            messages.error(request, "An event with the exact same title, date, time, and location already exists.")
            return redirect('admin_dashboard')

        new_event = Event.objects.create(
            id=uuid.uuid4(),
            admin_id=current_admin_id,
            title=title,
            description=description,
            date=date,
            location=location,
            start_time=start_time,
            end_time=end_time,
            max_attendees=int(max_attendees) if max_attendees and max_attendees.isdigit() else None,
            picture_url=None,
            manual_status_override='AUTO',
        )

        cache_key = f"dashboard_data_{current_admin_id}"
        cache.delete(cache_key)

        messages.success(request, f"Event '{title}' scheduled successfully!")
        response = redirect('admin_dashboard')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    if is_ajax:
        return render(request, 'fragments/create_event/create_event_content.html')

    return redirect('admin_dashboard')
