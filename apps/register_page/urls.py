# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_choice, name='register_choice'),
    path('register/student/', views.register_student, name='register_student'),
    path('register/administrator/', views.register_administrator, name='register_administrator'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('verify-student-otp/', views.verify_student_otp, name='verify_student_otp'),
    path('resend-student-otp/', views.resend_student_otp, name='resend_student_otp'),
    path('cleanup-and-register-student/', views.cleanup_and_register_student, name='cleanup_and_register_student'),
]