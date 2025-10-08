from django.urls import path, include

urlpatterns = [
    path('', include('apps.landing_page.urls')),
]