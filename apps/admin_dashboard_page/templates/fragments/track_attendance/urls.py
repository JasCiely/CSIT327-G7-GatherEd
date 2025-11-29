from django.urls import path
from . import views

urlpatterns = [
    path('', views.track_attendance, name='track_attendance'),  # /admin_dashboard/track/attendance/
]
