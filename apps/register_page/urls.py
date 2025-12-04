from django.urls import path
from . import views

urlpatterns = [
    # Registration URLs
    path('register/', views.register_choice, name='register_choice'),
    path('register/student/', views.register_student, name='register_student'),
    path('register/organizer-access/', views.pre_admin_register, name='pre_admin_register'),
    path('register/request-access-code/', views.request_access_code, name='request_access_code'),
    path('register/administrator/', views.register_administrator, name='register_administrator'),

    # OTP verification
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('verify-student-otp/', views.verify_student_otp, name='verify_student_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('resend-student-otp/', views.resend_student_otp, name='resend_student_otp'),
    path('cleanup-and-register/', views.cleanup_and_register, name='cleanup_and_register'),

    # One-Click Action URLs (from email) - These will be at /auth/one-click-action/
    path('one-click-action/<uuid:request_id>/approve/', views.one_click_approve, name='one_click_approve'),
    path('one-click-action/<uuid:request_id>/decline/', views.one_click_decline, name='one_click_decline'),

    # Admin review URLs (require login)
    path('access-code-requests/', views.access_code_request_list, name='access_code_request_list'),
    path('access-code-requests/review/<uuid:request_id>/', views.review_access_code_request,
         name='review_access_code_request'),

    path('register/administrator/', views.register_administrator, name='register_administrator'),
    path('register/administrator/<str:access_code>/', views.register_administrator, name='register_administrator_with_code'),

    # In your urls.py, add this line:
    path('cleanup-student-registration/', views.cleanup_pending_student_registration, name='cleanup_pending_student_registration'),
]