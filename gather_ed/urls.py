from django.urls import path, include

urlpatterns = [
    path('', include('apps.landing_page.urls')),
    path('', include('apps.register_page.urls')),
    path('', include('apps.login_page.urls')),
    path('admin_dashboard/', include('apps.admin_dashboard_page.urls')),
    path('', include('apps.admin_dashboard_page.templates.fragments.create_event.urls')),
    path('', include('apps.admin_dashboard_page.templates.fragments.manage_event.urls')),
    path('', include('apps.admin_dashboard_page.templates.fragments.manage_feedback.urls')),
    path('', include('apps.admin_dashboard_page.templates.fragments.track_attendance.urls')),

    path('student_dashboard/', include('apps.student_dashboard_page.urls')),
    path('', include('apps.student_dashboard_page.templates.fragments.event_list.urls')),
    path('', include('apps.student_dashboard_page.templates.fragments.my_events.urls')),
    path('', include('apps.student_dashboard_page.templates.fragments.notification.urls')),
    path('', include('apps.student_dashboard_page.templates.fragments.submit_feedback.urls')),
]