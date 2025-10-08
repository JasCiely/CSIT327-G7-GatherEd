from django.urls import path
from . import views

urlpatterns = [
    path('manage/feedback/', views.manage_feedback, name='manage_feedback'),
]