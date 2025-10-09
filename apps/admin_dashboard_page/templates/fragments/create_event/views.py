from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth.decorators import login_required
import uuid
import datetime

# CRITICAL IMPORT: Assuming this is the correct path where AdminProfile is defined.
from apps.register_page.models import AdminProfile


@login_required
def create_event(request):
    """
    Handles the creation of a new event, submitting data to Supabase via AJAX.
    Returns a success/error JSON response suitable for a client-side pop-up.
    """
    is_ajax = request.GET.get('is_ajax') == 'true'
    context = {}

    # 1. SUPABASE CLIENT INITIALIZATION
    try:
        supabase_admin: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    except AttributeError:
        error_msg = 'Server configuration error: Supabase service key is missing.'
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
        return redirect('admin_dashboard')

    # 2. VALIDATE & RETRIEVE ADMIN PROFILE
    try:
        admin_profile = get_object_or_404(AdminProfile, user=request.user)
        current_admin_id = admin_profile.pk

    except Exception:
        error_msg = 'Authentication error: Admin profile is missing in the database.'
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': error_msg}, status=403)
        return redirect('admin_dashboard')

    if request.method == 'POST':
        try:
            # --- FORM FIELD RETRIEVAL ---
            title = request.POST.get('title')
            description = request.POST.get('description')
            date = request.POST.get('date')
            location = request.POST.get('location')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            max_attendees = request.POST.get('max_attendees')

            # --- FIELD VALIDATION ---
            if not all([title, description, date, start_time]):
                return JsonResponse(
                    {'status': 'error', 'message': "Event title, description, date, and start time are required."},
                    status=400)

            # --- 3. INSERT RECORD INTO SUPABASE DATABASE ---
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
                error_dict = getattr(insert_result, 'error', {})
                error_message = error_dict.get('message', error_dict.get('details', 'Unknown database error'))
                raise Exception(f"Database insertion failed: {error_message}")

            # SUCCESS RESPONSE: This JSON triggers the SweetAlert2 Toast
            return JsonResponse({
                'status': 'success',
                'message': f"Event '{title}' scheduled successfully!",
            }, status=200)

        except Exception as e:
            # Catch all other errors (database, type conversion, etc.)
            return JsonResponse({'status': 'error', 'message': f"Failed to create event: {e}"}, status=500)

    # 4. HANDLE GET REQUEST (Renders the form fragment)
    else:
        if is_ajax:
            return render(request, 'fragments/create_event/create_event_content.html', context)
        else:
            return redirect('admin_dashboard')