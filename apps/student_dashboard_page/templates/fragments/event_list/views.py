from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def event_list(request):
    """
    Renders the fragment for viewing all available events for registration.
    (Features: View event details, Register button)
    """
    is_ajax = request.GET.get('is_ajax') == 'true'

    # Context ready for a list of event objects/dictionaries
    template_context = {'event_list': []}

    if is_ajax:
        # Renders the Event List fragment
        return render(request, 'fragments/event_list/event_list_content.html', template_context)
    return redirect('student_dashboard')