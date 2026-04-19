from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    path('login/', views.LoginView, name='login'),
    path('logout/', views.LogoutView, name='logout'),
    path('polling-unit-login/', views.PollingUnitLoginView, name='polling-unit-login'),
]
