from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views  
from . import views

app_name = 'habil'  # Register the namespace


urlpatterns = [
    path('admin/', admin.site.urls),
   
    path('', views.home, name='home'),  # Home Page
    path('about/', views.about, name='about'),  # About Page
    path('raw-sensor-data/', views.raw_sensor_data, name='raw_sensor_data'),  # Raw Sensor Data
    path('aqi-data/', views.aqi_data, name='aqi_data'),  # AQI Data
    path('aqi_results/', views.aqi_results, name='aqi_results'),  # AQI results
    path('predicted-values/', views.predicted_values, name='predicted_values'),  # Predictions
    path('sensor/<int:sensor_id>/', views.sensor_detail, name='sensor_detail'),  # Sensor Details
    path('sensor_data/', views.sensor_detail, name='sensor_data'),  # Sensor Data
    path('predicted_data/', views.predicted_data, name='predicted_data'),  # Predicted Data
    path('reports/', views.reports, name='reports'),  # Reports
    path('sensor_manager/', views.sensor_manager, name='sensor_manager'),  # Sensor Manager
    path('analytics/', include('analytics.urls')),  #analytics app urls
    path('signup/', views.signup, name='signup'),  # Signup
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),  # Activate Account
    path('fetch_sensor_data/<int:sensor_id>/', views.fetch_and_store_sensor_data, name='fetch_sensor_data'),
    path('aqi_trend/', views.aqi_trend, name='aqi_trend'),  # AQI Trend
    path('aqi_trend_data/', views.aqi_trend_data, name='aqi_trend_data'),
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='auth/logout.html', next_page='/'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('dashboard/', include(('dashboard.urls', 'dashboard'), namespace='habil')),

    

]