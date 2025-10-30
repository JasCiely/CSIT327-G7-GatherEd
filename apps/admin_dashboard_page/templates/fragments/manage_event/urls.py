from django.urls import path
from . import views

urlpatterns = [
    path('manage/', views.manage_events, name='manage_events_root'),
    path('manage/events/', views.manage_events, name='manage_event'),

    # AJAX Endpoint: The target for the JavaScript click event
    path('manage/event/<str:event_id>/details/', views.get_event_details_html, name='event_details_html'),

    # Modify/Edit View
    path('manage/event/<str:event_id>/modify/', views.modify_event_view, name='modify_event_root'),

    path('delete-event/<int:event_id>/', views.delete_event, name='delete_event'),
]
