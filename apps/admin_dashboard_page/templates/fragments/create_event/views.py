from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
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
        event_picture = request.FILES.get('event_image')

        # Basic validation
        if not all([title, description, date, start_time, location]):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False,
                                     'message': 'Event title, description, date, start time, and location are required.'})
            messages.error(request, "Event title, description, date, start time, and location are required.")
            return redirect('admin_dashboard')

        # Convert max_attendees safely
        try:
            max_attendees_int = int(max_attendees) if max_attendees and max_attendees.isdigit() else None
        except ValueError:
            max_attendees_int = None

        # Check for existing event
        existing_event = Event.objects.filter(
            admin_id=current_admin_id,
            title=title,
            date=date,
            start_time=start_time,
            location=location
        ).exists()

        if existing_event:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False,
                                     'message': 'An event with the exact same title, date, time, and location already exists.'})
            messages.error(request, "An event with the exact same title, date, time, and location already exists.")
            return redirect('admin_dashboard')

        try:
            # Create the event instance
            new_event = Event(
                id=uuid.uuid4(),
                admin_id=current_admin_id,
                title=title,
                description=description,
                date=date,
                location=location,
                start_time=start_time,
                end_time=end_time,
                max_attendees=max_attendees_int,
                manual_status_override='AUTO',
            )

            # Handle file upload
            if event_picture:
                # Validate file size (max 5MB)
                if event_picture.size > 5 * 1024 * 1024:
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': 'File size too large. Maximum 5MB allowed.'})
                    messages.error(request, "File size too large. Maximum 5MB allowed.")
                    return redirect('admin_dashboard')

                # Validate file type
                allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if event_picture.content_type not in allowed_types:
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': False,
                                             'message': 'Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.'})
                    messages.error(request, "Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.")
                    return redirect('admin_dashboard')

                # Save the file to the event instance
                new_event.picture = event_picture

            # Save the event
            new_event.save()

            # Clear relevant cache
            cache_key = f"dashboard_data_{current_admin_id}"
            cache.delete(cache_key)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f"Event '{title}' scheduled successfully!",
                    'redirect_url': '/admin_dashboard/'
                })

            messages.success(request, f"Event '{title}' scheduled successfully!")
            return redirect('admin_dashboard')

        except Exception as e:
            print(f"Error creating event: {str(e)}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'Error creating event: {str(e)}'})
            messages.error(request, f"Error creating event: {str(e)}")
            return redirect('admin_dashboard')

    if is_ajax:
        return render(request, 'fragments/create_event/create_event_content.html')

    return redirect('admin_dashboard')