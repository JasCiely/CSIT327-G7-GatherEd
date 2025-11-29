# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_choice, name='register_choice'),
    path('register/student/', views.register_student, name='register_student'),
    path('register/administrator/', views.register_administrator, name='register_administrator'),
]