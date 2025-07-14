from django.contrib.auth import views as auth_views
from django.urls import path

urlpatterns = [
    # ... other urls ...
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    # ... other urls ...
]