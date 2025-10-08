from django.urls import path
from . import views

urlpatterns = [
    path('events/my/', views.my_events, name='my_events'),
]