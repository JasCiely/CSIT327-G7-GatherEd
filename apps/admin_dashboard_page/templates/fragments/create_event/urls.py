from django.urls import path, include
from django.contrib import admin
from . import views

urlpatterns = [
    path('events/create/', views.create_event, name='create_event'),
]