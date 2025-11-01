from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.student_dashboard, name='student_dashboard'),
    path('logout/', views.logout_view, name='logout'),

    # Student features
    path('events/', include('apps.student_dashboard_page.templates.fragments.event_list.urls')),
    path('my-events/', include('apps.student_dashboard_page.templates.fragments.my_events.urls')),
    path('notifications/', include('apps.student_dashboard_page.templates.fragments.notification.urls')),
    path('submit-feedback/', include('apps.student_dashboard_page.templates.fragments.submit_feedback.urls')),
]
