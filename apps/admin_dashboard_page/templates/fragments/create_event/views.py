import uuid
import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth.decorators import login_required
from django.urls import reverse

@login_required
def create_event(request):
    """
    Handles the creation of a new event, submitting data to Supabase via AJAX.
    """
    is_ajax = request.GET.get('is_ajax') == 'true'
    context = {}

    try:
        supabase_admin: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    except AttributeError:
        if is_ajax:
            return JsonResponse(
                {'status': 'error', 'message': 'Server configuration error: Supabase service key is missing.'},
                status=500)
        return redirect('admin_dashboard')

    try:
        current_admin_id = request.user.pk
    except Exception:
        if is_ajax:
            return JsonResponse(
                {'status': 'error', 'message': 'Authentication error: Admin ID could not be determined.'}, status=401)
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

            # --- 2. INSERT RECORD INTO SUPABASE DATABASE ---
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
                error_message = getattr(insert_result, 'error', {}).get('message', 'Unknown database error')
                raise Exception(f"Database insertion failed: {error_message}")

            # --- SUCCESS RESPONSE (FOR AJAX) ---
            modify_url = reverse('modify_event', kwargs={'event_id': new_uuid})

            return JsonResponse({
                'status': 'success',
                'message': f"Event '{title}' scheduled successfully!",
                'event_data': insert_result.data[0],
                'modify_url': modify_url
            }, status=200)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Failed to create event: {e}"}, status=500)

    # --- 3. HANDLE GET REQUEST (Loading the Fragment) ---
    else:
        if is_ajax:
            # Template Path: admin_portal/fragments/create_event_content.html
            return render(request, 'fragments/create_event/create_event_content.html', context)
        else:
            return redirect('admin_dashboard')