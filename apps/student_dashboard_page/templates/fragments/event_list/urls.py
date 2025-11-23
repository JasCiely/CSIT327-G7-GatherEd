from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.event_list, name='event_list'),
    path('events/<uuid:event_id>/register/', views.register_event, name='register_event'),
]