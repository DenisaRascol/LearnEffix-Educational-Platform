from django.urls import path
from . import views

urlpatterns = [
    path('', views.loading_view, name='loading'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_elev, name='dashboard'),
    path('dashboard_profesor/', views.dashboard_profesor_view, name='dashboard_profesor'),
    path('register/', views.register_view, name='register'),
    path('home/', views.home_view, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('creeaza-clasa/', views.creeaza_clasa, name='creeaza_clasa'),
    path('clasa/<int:clasa_id>/', views.detalii_clasa, name='detalii_clasa'),
    path('clasa/<int:clasa_id>/incarcare/', views.incarcare_material, name='incarcare_material'),
    path('test/<int:test_id>/', views.detalii_test, name='detalii_test'),
    path('export_pdf/<int:test_id>/', views.export_pdf, name='export_pdf'),
    path('sterge_test/<int:test_id>/', views.sterge_test, name='sterge_test'),
    path('sterge-material/<int:material_id>/', views.sterge_material, name='sterge_material'),
    path('editare-test/<int:test_id>/', views.editare_test, name='editare_test'),
    path('dashboard-elev/', views.dashboard_elev, name='dashboard_elev'),
    path('inrolare/', views.inrolare_clasa, name='inrolare_clasa'),
    path('clasa-elev/<int:clasa_id>/', views.detalii_clasa_elev, name='detalii_clasa_elev'),
    path('test/<int:test_id>/sustine/', views.sustine_test, name='sustine_test'),
    path('test/<int:test_id>/rezultat/', views.calculeaza_rezultat, name='calculeaza_rezultat'),
]