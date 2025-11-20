# In your app's urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Event list for initial page load and full list refresh (AJAX)
    path('list/', views.event_list, name='event_list'),

    # AJAX endpoint for fetching full event details for the modal
    path('details/<int:event_id>/', views.event_details, name='event_details'),

    # AJAX endpoint for processing event registration (POST request)
    path('events/<int:event_id>/register/', views.register_event, name='register_event'),

    # Add your other paths here
]