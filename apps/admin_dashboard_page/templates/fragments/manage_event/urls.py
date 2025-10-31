# urls.py (in your app)
from django.urls import path
from . import views

urlpatterns = [
    path('manage/', views.manage_events, name='manage_events_root'),
    path('manage/events/', views.manage_events, name='manage_event'),

    # AJAX Endpoint: Details panel (e.g., when clicking a row)
    path('manage/event/<str:event_id>/details/', views.get_event_details_html, name='event_details_html'),

    # AJAX Endpoint: Handles both GET (load form) and POST (save form)
    path('manage/event/<str:event_id>/modify/', views.modify_event_root, name='modify_event_root'),

    # AJAX Endpoint: Deletion
    path('delete-event/<str:event_id>/', views.delete_event, name='delete_event'),
]