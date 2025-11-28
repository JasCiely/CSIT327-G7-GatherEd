from django.urls import path
from . import views

urlpatterns = [
    path('events/my/', views.my_events, name='my_events'),
    path('cancel_registration/<uuid:registration_id>/', views.cancel_registration, name='cancel_registration'),
]