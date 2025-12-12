# ============================================
# urls.py COMPLETO
# SIN rutas AJAX innecesarias
# ============================================

from django.urls import path
from . import views

urlpatterns = [
    # ============================================
    # AUTENTICACIÓN
    # ============================================
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ============================================
    # DASHBOARDS
    # ============================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # ============================================
    # RESERVAS
    # ============================================
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('nueva-reserva/', views.nueva_reserva, name='nueva_reserva'),
    path('eliminar-reserva/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),
    
    # ============================================
    # AJAX ENDPOINTS (Solo los que usas)
    # ============================================
    path('ajax/verificar-disponibilidad/', views.verificar_disponibilidad_ajax, name='verificar_disponibilidad_ajax'),
    path('ajax/calendario-ocupacion/', views.obtener_calendario_ocupacion_ajax, name='calendario_ocupacion_ajax'),
    
    # ============================================
    # ADMINISTRACIÓN
    # ============================================
    path('importar-usuarios/', views.importar_usuarios, name='importar_usuarios'),
    path('ver-usuarios/', views.ver_usuarios, name='ver_usuarios'),
]