from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('nueva-reserva/', views.nueva_reserva, name='nueva_reserva'),
    path('logout/', views.logout_view, name='logout'),
    path('importar-usuarios/', views.importar_usuarios, name='importar_usuarios'),
    path('ver-usuarios/', views.ver_usuarios, name='ver_usuarios'),
]