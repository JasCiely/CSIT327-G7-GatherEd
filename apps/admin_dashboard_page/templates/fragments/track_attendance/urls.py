from django.urls import path
from . import views

urlpatterns = [
    path('track/attendance/', views.track_attendance, name='track_attendance'),
]