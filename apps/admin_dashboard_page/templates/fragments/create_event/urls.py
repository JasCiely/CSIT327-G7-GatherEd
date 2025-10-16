from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_event, name='create_event'),  # /admin_dashboard/create/event/
]
