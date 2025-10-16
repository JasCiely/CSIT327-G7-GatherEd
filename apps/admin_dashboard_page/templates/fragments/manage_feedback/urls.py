from django.urls import path
from . import views

urlpatterns = [
    path('', views.manage_feedback, name='manage_feedback'),  # /admin_dashboard/manage/feedback/
]
