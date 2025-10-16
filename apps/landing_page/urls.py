from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('logout/', views.logout_view, name='logout'),
]