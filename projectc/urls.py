from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

app_name = 'habil'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('habil.urls')), 
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
   

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('analytics/', include('analytics.urls')),

]
