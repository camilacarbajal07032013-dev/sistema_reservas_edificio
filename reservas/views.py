from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum
from datetime import date, time, datetime, timedelta
from .models import Oficina, Espacio, Reserva
from django.utils import timezone

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
    
    from django.db.models import Sum
    from decimal import Decimal
    
    # Fechas para cálculos
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    hace_una_semana = hoy - timedelta(days=7)
    mes_actual = hoy.replace(day=1)
    mes_anterior = (mes_actual - timedelta(days=1)).replace(day=1)
    
    # 1. RESERVAS TOTALES y porcentaje mensual
    total_reservas = Reserva.objects.count()
    reservas_mes_actual = Reserva.objects.filter(fecha__gte=mes_actual, fecha__lte=hoy).count()
    reservas_mes_anterior = Reserva.objects.filter(fecha__gte=mes_anterior, fecha__lt=mes_actual).count()
    
    if reservas_mes_anterior > 0:
        crecimiento_mensual = ((reservas_mes_actual - reservas_mes_anterior) / reservas_mes_anterior) * 100
    else:
        crecimiento_mensual = 100 if reservas_mes_actual > 0 else 0
    
    # 2. RESERVAS HOY y porcentaje vs ayer
    reservas_hoy = Reserva.objects.filter(fecha=hoy).count()
    reservas_ayer = Reserva.objects.filter(fecha=ayer).count()
    
    if reservas_ayer > 0:
        crecimiento_diario = ((reservas_hoy - reservas_ayer) / reservas_ayer) * 100
    else:
        crecimiento_diario = 100 if reservas_hoy > 0 else 0
    
    # 3. HORAS TOTALES y porcentaje semanal
    # Calcular horas de esta semana
    reservas_esta_semana = Reserva.objects.filter(fecha__gte=hace_una_semana, fecha__lte=hoy)
    horas_esta_semana = 0
    for reserva in reservas_esta_semana:
        horas_esta_semana += reserva.duracion_horas()
    
    # Calcular horas de la semana anterior (hace 14 días a hace 7 días)
    hace_dos_semanas = hoy - timedelta(days=14)
    reservas_semana_anterior = Reserva.objects.filter(fecha__gte=hace_dos_semanas, fecha__lt=hace_una_semana)
    horas_semana_anterior = 0
    for reserva in reservas_semana_anterior:
        horas_semana_anterior += reserva.duracion_horas()
    
    if horas_semana_anterior > 0:
        crecimiento_semanal = ((horas_esta_semana - horas_semana_anterior) / horas_semana_anterior) * 100
    else:
        crecimiento_semanal = 100 if horas_esta_semana > 0 else 0
    
    # 4. OCUPACIÓN y porcentaje vs mes anterior
    # Obtener espacios activos
    espacios_activos = Espacio.objects.filter(activo=True).count()
    
    # Calcular capacidad total mensual (espacios * días del mes * horas promedio por día)
    dias_mes_actual = (hoy - mes_actual).days + 1
    horas_por_dia = 10  # Ajusta según tu operación (ej: 8AM a 6PM = 10 horas)
    capacidad_mes_actual = espacios_activos * dias_mes_actual * horas_por_dia
    
    # Ocupación actual
    if capacidad_mes_actual > 0:
        ocupacion_actual = (reservas_mes_actual * 100) / capacidad_mes_actual
    else:
        ocupacion_actual = 0
    
    # Ocupación mes anterior
    dias_mes_anterior = (mes_actual - mes_anterior).days
    capacidad_mes_anterior = espacios_activos * dias_mes_anterior * horas_por_dia
    
    if capacidad_mes_anterior > 0:
        ocupacion_anterior = (reservas_mes_anterior * 100) / capacidad_mes_anterior
    else:
        ocupacion_anterior = 0
    
    # Cambio en ocupación
    if ocupacion_anterior > 0:
        cambio_ocupacion = ocupacion_actual - ocupacion_anterior
    else:
        cambio_ocupacion = ocupacion_actual
    
    # HORARIO PICO - Mejorado
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
    
    # ESPACIO FAVORITO
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
        # Métricas principales
        'total_reservas': total_reservas,
        'reservas_hoy': reservas_hoy,
        'horas_totales': int(horas_esta_semana),
        'ocupacion': round(ocupacion_actual, 1),
        
        # Porcentajes de crecimiento/cambio
        'crecimiento_mensual': round(crecimiento_mensual, 1),
        'crecimiento_diario': round(crecimiento_diario, 1),
        'crecimiento_semanal': round(crecimiento_semanal, 1),
        'cambio_ocupacion': round(cambio_ocupacion, 1),
        
        # Otros datos
        'horario_pico': horario_pico[0],
        'porcentaje_pico': round((horario_pico[1] / total_reservas * 100), 0) if total_reservas > 0 else 0,
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
        bloques_horarios = request.POST.getlist('bloques_horarios')
        
        # Campos para estacionamientos
        nombre_visitante = request.POST.get('nombre_visitante', '')
        placa_visitante = request.POST.get('placa_visitante', '')
        empresa_visitante = request.POST.get('empresa_visitante', '')
        
        if not espacio_id or not fecha or not bloques_horarios:
            messages.error(request, 'Debe completar todos los campos obligatorios')
            return redirect('nueva_reserva')
        
        try:
            espacio = Espacio.objects.get(id=espacio_id)
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            
            # NUEVA VALIDACIÓN: Restricción de 30 minutos antes (CORREGIDO)
            ahora = timezone.now()  # Usar timezone.now() en lugar de datetime.now()
            hoy = ahora.date()
            
            # Solo aplicar restricción si la reserva es para hoy
            if fecha_obj == hoy:
                hora_actual_minutos = ahora.hour * 60 + ahora.minute
                
                for bloque in bloques_horarios:
                    if '-' not in bloque:
                        continue
                    
                    try:
                        hora_inicio_str, hora_fin_str = bloque.split('-')
                        hora_inicio_obj = datetime.strptime(hora_inicio_str, '%H:%M').time()
                        
                        # Convertir hora de inicio a minutos desde medianoche
                        minutos_inicio = hora_inicio_obj.hour * 60 + hora_inicio_obj.minute
                        
                        # Verificar si el bloque inicia en menos de 30 minutos
                        if minutos_inicio <= hora_actual_minutos + 30:
                            messages.error(request, 
                                f'No se puede reservar el horario {hora_inicio_str}-{hora_fin_str} '
                                f'porque debe hacerse al menos 30 minutos antes de la hora de inicio.'
                            )
                            return redirect('nueva_reserva')
                    except ValueError:
                        messages.error(request, f'Formato de hora inválido: {bloque}')
                        return redirect('nueva_reserva')
            
            # Validar límites según tipo de espacio
            if espacio.tipo.lower() in ['sala'] and len(bloques_horarios) > 2:
                messages.error(request, 'Las salas permiten máximo 2 bloques por día')
                return redirect('nueva_reserva')
            elif 'directorio' in espacio.tipo.lower() and len(bloques_horarios) > 2:
                messages.error(request, 'El directorio permite máximo 2 bloques por día')
                return redirect('nueva_reserva')
            
            reservas_creadas = 0
            
            for bloque in bloques_horarios:
                if '-' not in bloque:
                    continue
                    
                try:
                    hora_inicio_str, hora_fin_str = bloque.split('-')
                    hora_inicio_obj = datetime.strptime(hora_inicio_str, '%H:%M').time()
                    hora_fin_obj = datetime.strptime(hora_fin_str, '%H:%M').time()
                    
                    # Verificar conflictos
                    conflicto = Reserva.objects.filter(
                        espacio=espacio,
                        fecha=fecha_obj,
                        hora_inicio__lt=hora_fin_obj,
                        hora_fin__gt=hora_inicio_obj
                    ).exists()
                    
                    if conflicto:
                        messages.error(request, f'Conflicto en horario {hora_inicio_str}-{hora_fin_str}')
                        return redirect('nueva_reserva')
                    
                    # Crear reserva individual para este bloque
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
                    reservas_creadas += 1
                    
                except ValueError:
                    messages.error(request, f'Formato inválido: {bloque}')
                    return redirect('nueva_reserva')
            
            if reservas_creadas > 0:
                messages.success(request, f'Se crearon {reservas_creadas} reserva(s) exitosamente!')
                return redirect('mis_reservas')
            else:
                messages.error(request, 'No se pudo crear ninguna reserva')
                return redirect('nueva_reserva')
                
        except Exception as e:
            messages.error(request, f'Error al crear la reserva: {str(e)}')
            return redirect('nueva_reserva')
    
    # GET request
    espacios = Espacio.objects.filter(
        Q(activo=True) & (
            Q(tipo__in=['sala', 'directorio', 'terraza']) |
            Q(tipo='estacionamiento', es_estacionamiento_visita=True) |
            Q(tipo='estacionamiento', oficina_propietaria=oficina)
        )
    )
    
    # Obtener fecha y hora actual del servidor usando timezone
    ahora_servidor = timezone.now()
    fecha_hoy_servidor = ahora_servidor.strftime('%Y-%m-%d')
    hora_actual_minutos = ahora_servidor.hour * 60 + ahora_servidor.minute
    
    context = {
        'espacios': espacios,
        'fecha_minima': date.today().isoformat(),
        'fecha_hoy': fecha_hoy_servidor,  # NUEVO
        'hora_actual_minutos': hora_actual_minutos,  # NUEVO
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