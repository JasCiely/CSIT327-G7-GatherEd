from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def get_notifications(request):
    is_ajax = request.GET.get('is_ajax') == 'true'

    template_context = {
        'notifications_list': [],
    }

    if is_ajax:
        return render(request, 'fragments/notification/notifications_content.html', template_context)
    return redirect('student_dashboard')