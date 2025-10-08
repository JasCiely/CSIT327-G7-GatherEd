# C:\Projects\CSIT327-G7-GatherEd\apps\admin_dashboard_page\urls.py

from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),

    path('manage/events/', include('apps.admin_dashboard_page.templates.fragments.manage_event.urls')),

    path('create/event/', include('apps.admin_dashboard_page.templates.fragments.create_event.urls')),

    path('track/attendance/', include('apps.admin_dashboard_page.templates.fragments.track_attendance.urls')),

    path('manage/feedback/', include('apps.admin_dashboard_page.templates.fragments.manage_feedback.urls')),
]