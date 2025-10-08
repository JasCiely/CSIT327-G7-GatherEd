from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def my_events(request):
    is_ajax = request.GET.get('is_ajax') == 'true'

    template_context = {'my_events_list': []}

    if is_ajax:
        return render(request, 'fragments/my_events/my_events_content.html', template_context)
    return redirect('student_dashboard')