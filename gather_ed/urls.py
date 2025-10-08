from django.urls import path, include

urlpatterns = [
    path('', include('apps.landing_page.urls')),
    path('', include('apps.register_page.urls')),
    path('', include('apps.login_page.urls')),

]