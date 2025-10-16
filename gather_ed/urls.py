from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Landing, Register, Login pages
    path('', include('apps.landing_page.urls')),
    path('', include('apps.register_page.urls')),
    path('', include('apps.login_page.urls')),

    # Admin dashboard and features
    path('admin_dashboard/', include('apps.admin_dashboard_page.urls')),

    # Student dashboard and features
    path('student_dashboard/', include('apps.student_dashboard_page.urls')),
]
