from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def submit_feedback(request):

    is_ajax = request.GET.get('is_ajax') == 'true'

    template_context = {'events_for_feedback': []}

    if is_ajax:
        return render(request, 'fragments/submit_feedback/submit_feedback_content.html', template_context)
    return redirect('student_dashboard')