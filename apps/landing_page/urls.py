from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('register/', TemplateView.as_view(template_name='users/register.html'), name='register'),
    path('login/', TemplateView.as_view(template_name='users/login.html'), name='login'),
]