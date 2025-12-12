from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Reservas
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('nueva-reserva/', views.nueva_reserva, name='nueva_reserva'),
    path('eliminar-reserva/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),
    
    # AJAX Endpoints (MANTENER TUS ENDPOINTS EXISTENTES)
    path('ajax/verificar-disponibilidad/', views.verificar_disponibilidad_ajax, name='verificar_disponibilidad_ajax'),
    path('ajax/calendario-ocupacion/', views.obtener_calendario_ocupacion_ajax, name='calendario_ocupacion_ajax'),
    
    # ⭐ NUEVO ENDPOINT PARA HORARIOS ⭐
    path('obtener-horarios/', views.obtener_horarios, name='obtener_horarios'),
    
    # Utilidades
    path('importar-usuarios/', views.importar_usuarios, name='importar_usuarios'),
    path('ver-usuarios/', views.ver_usuarios, name='ver_usuarios'),
]