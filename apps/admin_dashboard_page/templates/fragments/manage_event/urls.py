from django.urls import path
from . import views

urlpatterns = [
    path('', views.manage_events, name='manage_event'),  # /admin_dashboard/manage/events/
    path('modify/<uuid:event_id>/', views.modify_event_view, name='modify_event'),
]
