from django.urls import path
from . import views

urlpatterns = [
    path('', views.loading_view, name='loading'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard_profesor/', views.dashboard_profesor_view, name='dashboard_profesor'),
    path('register/', views.register_view, name='register'),
    path('home/', views.home_view, name='home'),
    path('incarcare-material/', views.incarcare_material, name='incarcare_material'),
    path('logout/', views.logout_view, name='logout'),
    path('incarcare/', views.incarcare_material, name='incarcare_material'),
    path('test/<int:test_id>/', views.detalii_test_view, name='detalii_test'),
]