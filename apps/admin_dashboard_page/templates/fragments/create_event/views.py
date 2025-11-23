# apps/admin_dashboard_page/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
import uuid
import os

# Assuming your models and utilities are structured like this:
from apps.register_page.models import AdminProfile
from apps.admin_dashboard_page.models import Event
from apps.utils.supabase_utils import upload_file_to_supabase


@login_required
def create_event(request):
    admin_profile = get_object_or_404(AdminProfile, user=request.user)
    current_admin_id = admin_profile.pk
    # Check if the request is an AJAX call (from the frontend's fetch)
    is_fetch_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        # Retrieve all fields
        title = request.POST.get('title')
        description = request.POST.get('description')
        date = request.POST.get('date')
        location = request.POST.get('location')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        max_attendees = request.POST.get('max_attendees')

        # Retrieve optional manual override fields
        manual_status_override = request.POST.get('manual_status_override', 'AUTO')
        manual_close_date = request.POST.get('manual_close_date')
        manual_close_time = request.POST.get('manual_close_time')

        event_image = request.FILES.get('event_image')  # Retrieve the uploaded file

        # --- 1. Basic Validation ---
        if not all([title, description, date, start_time, location]):
            error_message = "Event title, description, date, start time, and location are required."
            if is_fetch_request:
                return JsonResponse({'success': False, 'message': error_message}, status=400)
            messages.error(request, error_message)
            return redirect('admin_dashboard')

        # ORM Check: Use ORM to check for existing events
        if Event.objects.filter(admin_id=current_admin_id, title=title, date=date, start_time=start_time,
                                location=location).exists():
            error_message = "An event with the exact same details already exists."
            if is_fetch_request:
                return JsonResponse({'success': False, 'message': error_message}, status=409)
            messages.error(request, error_message)
            return redirect('admin_dashboard')

        # Pre-generate UUID for stable file naming
        event_id = uuid.uuid4()
        picture_url = None

        # --- 2. Supabase File Upload (External Storage) ---
        if event_image:
            file_ext = os.path.splitext(event_image.name)[1]
            # Create a path unique to the admin and event for organization
            file_path = f"events/{current_admin_id}/{event_id}{file_ext}"

            picture_url = upload_file_to_supabase(event_image, file_path)

            if not picture_url:
                error_message = "Failed to upload event image to storage. Event not created."
                if is_fetch_request:
                    return JsonResponse({'success': False, 'message': error_message}, status=500)
                messages.error(request, error_message)
                return redirect('admin_dashboard')

        # --- 3. ORM Creation (Database Write) ---
        try:
            # Use the ORM to create the new record in the database
            Event.objects.create(
                id=event_id,
                admin_id=current_admin_id,
                # Foreign Key: Ensure this matches the field name in your model (AdminProfile object is passed)
                title=title,
                description=description,
                date=date,
                location=location,
                start_time=start_time,
                end_time=end_time,
                max_attendees=int(max_attendees) if max_attendees and str(max_attendees).isdigit() else None,
                picture_url=picture_url,  # **CRITICAL: Saves the external URL in the ORM field**

                # Manual Override fields
                manual_status_override=manual_status_override,
                manual_close_date=manual_close_date,
                manual_close_time=manual_close_time,
            )

            # Clear cache and send success response
            cache.delete(f"dashboard_data_{current_admin_id}")
            success_message = f"Event '{title}' scheduled successfully!"

            if is_fetch_request:
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'redirect_url': '/admin_dashboard/'
                })

            messages.success(request, success_message)
            return redirect('admin_dashboard')

        except Exception as e:
            # Handle any ORM-specific database error
            error_message = f"An error occurred during event creation: {e}"
            if is_fetch_request:
                return JsonResponse({'success': False, 'message': error_message}, status=500)
            messages.error(request, error_message)
            return redirect('admin_dashboard')

    # Handle GET request (for fragment or default redirection)
    is_ajax = request.GET.get('is_ajax') == 'true'
    if is_ajax:
        # Use HttpResponse for fragments if the frontend expects a specific content type
        return render(request, 'fragments/create_event/create_event_content.html')

    return redirect('admin_dashboard')