from django.urls import path
from . import views

urlpatterns = [
    path('manage/events/', views.manage_events, name='manage_event'),
    path('modify/<uuid:event_id>/', views.modify_event_view, name='modify_event'),
]