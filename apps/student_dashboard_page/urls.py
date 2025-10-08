from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_dashboard_view, name='student_dashboard'),

]