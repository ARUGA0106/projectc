from django.urls import path
from . import views
app_name = 'dashboard'  # Register the namespace
urlpatterns = [
    path('', views.dashboard_home, name='dashboard'),
    path('data-management/', views.data_management, name='data_management'),
    path('alerts/', views.alerts, name='alerts'),
    path('chatbot-api/', views.chatbot_api, name='chatbot_api'),
    # ...other dashboard URLs...
    path('add-user/', views.add_user, name='add_user'),
   # path('add-sensor/', views.add_sensor, name='add_sensor'),
    path('user-management/', views.user_management, name='user_management'),
    path('user-management/deactivate/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('user-management/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('sensor-management/', views.sensor_management, name='sensor_management'),
    path('sensor-management/toggle/<int:sensor_id>/', views.toggle_sensor_status, name='toggle_sensor_status'),
    path('report/download/', views.download_report, name='download_report'),
    path('report/form/', views.report_form, name='report_form'),
    path('sensor-management/delete/<int:sensor_id>/', views.delete_sensor, name='delete_sensor'),
]