from django.urls import path
from . import views

urlpatterns = [
    path('', views.analytics_dashboard, name='analytics_dashboard'),
    path('sensors/', views.sensor_dashboard, name='sensor_dashboard'),
]