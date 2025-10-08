from django.urls import path
from . import views

urlpatterns = [
    path('manage/events/', views.manage_events, name='manage_event'),
]