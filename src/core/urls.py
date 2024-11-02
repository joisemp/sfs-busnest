from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
     path('login/', views.LoginView.as_view(), name='login'),
     path('register/', views.UserRegisterView.as_view(), name='register'),
     path('logout/', views.LogoutView.as_view(), name='logout'),
]