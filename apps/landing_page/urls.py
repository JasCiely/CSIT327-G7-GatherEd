# apps/landing_page/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('logout/', views.logout_view, name='logout'),
]