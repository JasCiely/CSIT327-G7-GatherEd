# apps/dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('student/', views.student_dashboard_view, name='student_dashboard'),
    path('logout/', views.logout_view, name='logout'),
]
