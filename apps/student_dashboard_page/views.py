from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages

# Assuming this import path is correct based on your snippet
from apps.register_page.models import StudentProfile


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    response = redirect('index')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def student_dashboard(request):
    is_ajax = request.GET.get('is_ajax') == 'true'

    # 🌟 FETCH LOGIC: Get the student's name from StudentProfile
    try:
        student_profile = StudentProfile.objects.get(user=request.user)
        # Use the 'name' field from your StudentProfile model
        user_display_name = student_profile.name
    except StudentProfile.DoesNotExist:
        # Fallback to email if a profile hasn't been created for the user
        user_display_name = request.user.email

    template_context = {
        'upcoming_events_count': 0,
        'total_registered_count': 0,
        'events_attended_count': 0,
        'next_event': None,
        # PASS THE NAME: This variable is used in the HTML
        'user_display_name': user_display_name,
    }

    if is_ajax:
        return render(request, 'fragments/dashboard_content.html', template_context)
    else:
        # Pass the context to the main dashboard template
        return render(request, 'student_dashboard.html', template_context)