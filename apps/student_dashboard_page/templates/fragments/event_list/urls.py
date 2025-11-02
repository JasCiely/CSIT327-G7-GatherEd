# apps/student_dashboard_page/templates/fragments/event_list/views.py
from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.event_list, name='event_list'),
]