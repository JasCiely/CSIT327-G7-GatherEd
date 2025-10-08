from django.urls import path
from . import views

urlpatterns = [
    path('events/list/', views.event_list, name='event_list'),
]