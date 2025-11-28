from django.urls import path
from . import views

urlpatterns = [
    # Main page for viewing the attendance tracker
    path('', views.track_attendance, name='track_attendance'),

    # API endpoint to fetch students for a selected event
    path('api/get-students/<uuid:event_id>/', views.get_event_students, name='get_event_students'),

    # API endpoint to record/update attendance
    path('api/record-attendance/', views.record_attendance, name='record_attendance'),
]