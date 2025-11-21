from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

from gather_ed import settings

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

if settings.DEBUG:
    # Serve media files (user uploads)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve static files (CSS/JS/images)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)