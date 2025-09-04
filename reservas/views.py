from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum
from datetime import date, time, datetime, timedelta
from .models import Oficina, Espacio, Reserva

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'reservas/login.html')

@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('mis_reservas')

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('mis_reservas')
    
    # Estadísticas
    total_reservas = Reserva.objects.count()
    reservas_hoy = Reserva.objects.filter(fecha=date.today()).count()
    
    # Calcular horas totales
    horas_totales = Reserva.objects.aggregate(Sum('duracion_horas'))['duracion_horas__sum'] or 0
    
    # Porcentaje de ocupación (ejemplo: 4 espacios * 10 horas * 30 días = 1200h máximo)
    capacidad_total = 4 * 10 * 30  # Ajusta según tus espacios reales
    ocupacion = round((horas_totales / capacidad_total * 100), 1) if capacidad_total > 0 else 0
    
    # HORARIO PICO - Analizar qué franja horaria tiene más reservas
    horarios_count = {}
    reservas_con_hora = Reserva.objects.all()
    
    for reserva in reservas_con_hora:
        hora = reserva.hora_inicio.hour
        if 8 <= hora < 12:
            franja = "Mañanas (8AM-12PM)"
        elif 12 <= hora < 16:
            franja = "Tardes (12PM-4PM)"  
        elif 16 <= hora < 20:
            franja = "Tardes (4PM-8PM)"
        else:
            franja = "Otras horas"
            
        horarios_count[franja] = horarios_count.get(franja, 0) + 1
    
    horario_pico = max(horarios_count.items(), key=lambda x: x[1]) if horarios_count else ("No definido", 0)
    
    # CRECIMIENTO - Comparar último mes vs anterior
    hoy = date.today()
    mes_actual = hoy.replace(day=1)
    mes_anterior = (mes_actual - timedelta(days=1)).replace(day=1)
    
    reservas_mes_actual = Reserva.objects.filter(fecha__gte=mes_actual).count()
    reservas_mes_anterior = Reserva.objects.filter(
        fecha__gte=mes_anterior, 
        fecha__lt=mes_actual
    ).count()
    
    if reservas_mes_anterior > 0:
        crecimiento = ((reservas_mes_actual - reservas_mes_anterior) / reservas_mes_anterior) * 100
    else:
        crecimiento = 100 if reservas_mes_actual > 0 else 0
    
    # ESPACIO FAVORITO - Espacio más reservado
    espacio_favorito = Reserva.objects.values(
        'espacio__nombre'
    ).annotate(
        total=Count('id')
    ).order_by('-total').first()
    
    # Top oficinas
    oficinas_activas = Oficina.objects.annotate(
        total_reservas=Count('reserva')
    ).order_by('-total_reservas')[:10]
    
    # Reservas recientes
    reservas_recientes = Reserva.objects.select_related(
        'oficina', 'espacio'
    ).order_by('-fecha_creacion')[:15]
    
    context = {
        'total_reservas': total_reservas,
        'reservas_hoy': reservas_hoy,
        'horas_totales': horas_totales,
        'ocupacion': ocupacion,
        'horario_pico': horario_pico[0],
        'porcentaje_pico': round((horario_pico[1] / total_reservas * 100), 0) if total_reservas > 0 else 0,
        'crecimiento': round(crecimiento, 1),
        'espacio_favorito': espacio_favorito['espacio__nombre'] if espacio_favorito else 'No definido',
        'porcentaje_favorito': round((espacio_favorito['total'] / total_reservas * 100), 0) if espacio_favorito and total_reservas > 0 else 0,
        'oficinas_activas': oficinas_activas,
        'reservas_recientes': reservas_recientes,
    }
    return render(request, 'reservas/admin_dashboard.html', context)

@login_required
def mis_reservas(request):
    try:
        oficina = request.user.oficina
        reservas = Reserva.objects.filter(oficina=oficina).order_by('-fecha')
        
        context = {
            'reservas': reservas,
            'oficina': oficina,
        }
        return render(request, 'reservas/mis_reservas.html', context)
    except:
        messages.error(request, 'No se encontró información de la oficina')
        return redirect('login')

@login_required
def nueva_reserva(request):
    try:
        oficina = request.user.oficina
    except:
        messages.error(request, 'Error: Oficina no encontrada')
        return redirect('login')
    
    if request.method == 'POST':
        espacio_id = request.POST.get('espacio')
        fecha = request.POST.get('fecha')
        bloque_horario = request.POST.get('bloque_horario')
        if bloque_horario and '-' in bloque_horario:
            hora_inicio_str, hora_fin_str = bloque_horario.split('-')
            hora_inicio_obj = datetime.strptime(hora_inicio_str, '%H:%M').time()
            hora_fin_obj = datetime.strptime(hora_fin_str, '%H:%M').time()
        else:
            messages.error(request, 'Debe seleccionar un bloque de horario válido')
        
        # Campos para estacionamientos
        nombre_visitante = request.POST.get('nombre_visitante', '')
        placa_visitante = request.POST.get('placa_visitante', '')
        empresa_visitante = request.POST.get('empresa_visitante', '')
        
        # Validaciones básicas
        try:
            espacio = Espacio.objects.get(id=espacio_id)
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            
            # Verificar que no haya conflictos
            conflicto = Reserva.objects.filter(
                espacio=espacio,
                fecha=fecha_obj,
                hora_inicio__lt=hora_fin_obj,
                hora_fin__gt=hora_inicio_obj
            ).exists()
            
            if conflicto:
                messages.error(request, 'Ya hay una reserva en ese horario')
            else:
                # Crear la reserva
                Reserva.objects.create(
                    oficina=oficina,
                    espacio=espacio,
                    fecha=fecha_obj,
                    hora_inicio=hora_inicio_obj,
                    hora_fin=hora_fin_obj,
                    nombre_visitante=nombre_visitante,
                    placa_visitante=placa_visitante,
                    empresa_visitante=empresa_visitante
                )
                messages.success(request, 'Reserva creada exitosamente!')
                return redirect('mis_reservas')
            
                
        except Exception as e:
            messages.error(request, f'Error al crear la reserva: {str(e)}')
    
    # Obtener espacios disponibles
    espacios = Espacio.objects.filter(
        Q(activo=True) & (
            Q(tipo__in=['sala', 'directorio', 'terraza']) |  # Espacios comunes
            Q(tipo='estacionamiento', es_estacionamiento_visita=True) |  # Estacionamientos de visita
            Q(tipo='estacionamiento', oficina_propietaria=oficina)  # Sus estacionamientos propios
        )
    )
    
    # Horarios disponibles por tipo de espacio
    horarios = []
    horarios_bloques = {
        'directorio': [
            {'inicio': '08:00', 'fin': '10:00', 'label': '8:00 AM - 10:00 AM'},
            {'inicio': '10:15', 'fin': '12:15', 'label': '10:15 AM - 12:15 PM'},
            {'inicio': '13:00', 'fin': '15:00', 'label': '1:00 PM - 3:00 PM'},
            {'inicio': '15:15', 'fin': '17:15', 'label': '3:15 PM - 5:15 PM'},
        ],
        'sala': [
            {'inicio': '08:00', 'fin': '09:00', 'label': '8:00 AM - 9:00 AM'},
            {'inicio': '09:00', 'fin': '10:00', 'label': '9:00 AM - 10:00 AM'},
            {'inicio': '10:00', 'fin': '11:00', 'label': '10:00 AM - 11:00 AM'},
            # ... agregar más horarios de salas
        ],
        'terraza': [
            {'inicio': '08:00', 'fin': '10:00', 'label': '8:00 AM - 10:00 AM'},
            {'inicio': '10:00', 'fin': '12:00', 'label': '10:00 AM - 12:00 PM'},
            {'inicio': '14:00', 'fin': '16:00', 'label': '2:00 PM - 4:00 PM'},
            {'inicio': '16:00', 'fin': '18:00', 'label': '4:00 PM - 6:00 PM'},
        ]
    }
    
    context = {
        'espacios': espacios,
        'horarios_bloques': horarios_bloques,
        'fecha_minima': date.today().isoformat(),
    }
    return render(request, 'reservas/nueva_reserva.html', context)

def logout_view(request):
    logout(request)
    return redirect('login')

def importar_usuarios(request):
    from django.http import HttpResponse
    from django.core.management import call_command
    from django.contrib.auth.models import User
    import os
    
    try:
        # Buscar archivos disponibles
        archivo = None
        for nombre in ['usuarios_limpio.json', 'usuarios_utf8.json', 'usuarios.json']:
            if os.path.exists(nombre):
                archivo = nombre
                break
        
        if not archivo:
            return HttpResponse("❌ Ningún archivo de usuarios encontrado")
        
        # Contar usuarios antes
        usuarios_antes = User.objects.count()
        
        # Importar datos
        call_command('loaddata', archivo)
        
        # Contar usuarios después
        usuarios_despues = User.objects.count()
        
        return HttpResponse(f"✅ Importación exitosa usando {archivo}!<br>Usuarios antes: {usuarios_antes}<br>Usuarios después: {usuarios_despues}")
        
    except Exception as e:
        return HttpResponse(f"❌ Error al importar: {str(e)}")

def ver_usuarios(request):
    from django.http import HttpResponse
    from django.contrib.auth.models import User
    
    usuarios = User.objects.all()
    lista = "<br>".join([f"- {u.username} (activo: {u.is_active})" for u in usuarios])
    return HttpResponse(f"<h3>Usuarios en Railway ({usuarios.count()} total):</h3><br>{lista}")