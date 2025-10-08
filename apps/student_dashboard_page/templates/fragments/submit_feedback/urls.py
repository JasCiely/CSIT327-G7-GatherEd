from django.urls import path
from . import views

urlpatterns = [
    path('feedback/submit/', views.submit_feedback, name='submit_feedback'),
]