from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from datetime import date, time, datetime, timedelta
from .models import Oficina, Espacio, Reserva
import json

def agrupar_reservas_consecutivas(reservas_query):
    """
    Agrupa reservas consecutivas del mismo espacio, fecha y oficina
    """
    reservas = list(reservas_query)
    if not reservas:
        return []
    
    agrupadas = []
    i = 0
    
    while i < len(reservas):
        grupo = [reservas[i]]
        j = i + 1
        
        # Buscar reservas consecutivas
        while j < len(reservas):
            anterior = grupo[-1]
            actual = reservas[j]
            
            # Verificar si son consecutivas
            if (anterior.oficina == actual.oficina and
                anterior.espacio == actual.espacio and
                anterior.fecha == actual.fecha and
                anterior.hora_fin == actual.hora_inicio):
                grupo.append(actual)
                j += 1
            else:
                break
        
        # Crear objeto de reserva agrupada
        if len(grupo) > 1:
            # Si hay múltiples reservas, crear una agrupada
            primera = grupo[0]
            ultima = grupo[-1]
            
            # Crear un objeto similar a Reserva pero con datos combinados
            class ReservaAgrupada:
                def __init__(self, reservas_grupo):
                    self.oficina = reservas_grupo[0].oficina
                    self.espacio = reservas_grupo[0].espacio
                    self.fecha = reservas_grupo[0].fecha
                    self.hora_inicio = reservas_grupo[0].hora_inicio
                    self.hora_fin = reservas_grupo[-1].hora_fin
                    self.fecha_creacion = reservas_grupo[0].fecha_creacion
                    self.nombre_visitante = reservas_grupo[0].nombre_visitante
                    self.placa_visitante = reservas_grupo[0].placa_visitante
                    self.empresa_visitante = reservas_grupo[0].empresa_visitante
                    self._duracion = sum(r.duracion_horas() for r in reservas_grupo)
                    self.es_agrupada = True
                    
                def duracion_horas(self):
                    return self._duracion
            
            agrupadas.append(ReservaAgrupada(grupo))
        else:
            # Si es una sola reserva, agregarla tal cual
            grupo[0].es_agrupada = False
            agrupadas.append(grupo[0])
        
        i = j
    
    return agrupadas

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

# Reemplaza tu función admin_dashboard en views.py con esta versión corregida

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
    
    # Top oficinas CON CÁLCULOS REALES DE PROMEDIO
    oficinas_activas = Oficina.objects.annotate(
        total_reservas=Count('reserva', filter=Q(reserva__fecha__gte=mes_actual, reserva__fecha__lte=hoy))
    ).order_by('-total_reservas')[:10]
    
    # CALCULAR PROMEDIO REAL DE HORAS POR OFICINA
    for oficina in oficinas_activas:
        # Obtener todas las reservas de esta oficina este mes
        reservas_oficina = Reserva.objects.filter(
            oficina=oficina,
            fecha__gte=mes_actual,
            fecha__lte=hoy
        )
        
        if reservas_oficina.count() > 0:
            horas_totales_oficina = sum(r.duracion_horas() for r in reservas_oficina)
            oficina.promedio_horas = round(horas_totales_oficina / reservas_oficina.count(), 1)
            oficina.horas_totales_mes = int(horas_totales_oficina)
        else:
            oficina.promedio_horas = 0
            oficina.horas_totales_mes = 0
        
        # Calcular porcentaje de la barra (basado en máximo 20 reservas = 100%)
        oficina.porcentaje_barra = min((oficina.total_reservas / 20) * 100, 100) if oficina.total_reservas > 0 else 0
    
    # Reservas recientes
    reservas_query = Reserva.objects.select_related(
        'oficina', 'espacio'
    ).order_by('oficina', 'espacio', 'fecha', 'hora_inicio')[:50]
    reservas_recientes = agrupar_reservas_consecutivas(reservas_query)
    
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
        reservas_query = Reserva.objects.filter(oficina=oficina).order_by('fecha', 'espacio', 'hora_inicio')
        reservas = agrupar_reservas_consecutivas(reservas_query)
        
        # ===== CÁLCULOS DINÁMICOS PARA ESTADÍSTICAS =====
        
        # 1. Calcular horas totales reservadas este mes
        from datetime import date, timedelta
        hoy = date.today()
        primer_dia_mes = hoy.replace(day=1)
        
        reservas_este_mes = Reserva.objects.filter(
            oficina=oficina,
            fecha__gte=primer_dia_mes,
            fecha__lte=hoy
        )
        
        horas_este_mes = 0
        for reserva in reservas_este_mes:
            horas_este_mes += reserva.duracion_horas()
        
        # 2. Encontrar espacio favorito (más usado)
        from django.db.models import Count
        espacio_favorito = Reserva.objects.filter(
            oficina=oficina
        ).values(
            'espacio__nombre'
        ).annotate(
            total=Count('id')
        ).order_by('-total').first()
        
        espacio_favorito_nombre = espacio_favorito['espacio__nombre'] if espacio_favorito else 'Ninguno'
        
        # 3. Calcular ranking de la oficina (comparar con otras)
        # Contar reservas de esta oficina este mes
        mis_reservas_mes = reservas_este_mes.count()
        
        # Contar reservas de todas las oficinas este mes y rankear
        todas_las_oficinas = Oficina.objects.annotate(
            reservas_mes=Count(
                'reserva',
                filter=Q(reserva__fecha__gte=primer_dia_mes, reserva__fecha__lte=hoy)
            )
        ).order_by('-reservas_mes')
        
        mi_ranking = 1
        for i, otra_oficina in enumerate(todas_las_oficinas, 1):
            if otra_oficina.id == oficina.id:
                mi_ranking = i
                break
        
        # 4. Calcular estadísticas adicionales
        total_reservas_activas = reservas.filter(fecha__gte=hoy).count()
        reservas_pasadas = reservas.filter(fecha__lt=hoy).count()
        
        # 5. Próximas reservas (las 3 más cercanas)
        proximas_reservas = reservas.filter(fecha__gte=hoy).order_by('fecha', 'hora_inicio')[:3]
        
        # 6. Calcular promedio de horas por reserva
        if reservas_este_mes.count() > 0:
            promedio_horas = horas_este_mes / reservas_este_mes.count()
        else:
            promedio_horas = 0
        
        # 7. Comparación con mes anterior
        mes_anterior = (primer_dia_mes - timedelta(days=1)).replace(day=1)
        fin_mes_anterior = primer_dia_mes - timedelta(days=1)
        
        reservas_mes_anterior = Reserva.objects.filter(
            oficina=oficina,
            fecha__gte=mes_anterior,
            fecha__lte=fin_mes_anterior
        )
        
        horas_mes_anterior = 0
        for reserva in reservas_mes_anterior:
            horas_mes_anterior += reserva.duracion_horas()
        
        # Calcular crecimiento
        if horas_mes_anterior > 0:
            crecimiento_porcentaje = ((horas_este_mes - horas_mes_anterior) / horas_mes_anterior) * 100
        else:
            crecimiento_porcentaje = 100 if horas_este_mes > 0 else 0
        
        # 8. Distribución por tipo de espacio
        tipos_espacios = Reserva.objects.filter(
            oficina=oficina
        ).values(
            'espacio__tipo'
        ).annotate(
            cantidad=Count('id')
        ).order_by('-cantidad')
        
        context = {
            'reservas': reservas,
            'oficina': oficina,
            
            # ESTADÍSTICAS DINÁMICAS
            'total_reservas_activas': total_reservas_activas,
            'horas_este_mes': int(horas_este_mes),
            'reservas_este_mes': reservas_este_mes.count(),
            'espacio_favorito': espacio_favorito_nombre,
            'mi_ranking': mi_ranking,
            'total_oficinas': todas_las_oficinas.count(),
            
            # ESTADÍSTICAS ADICIONALES
            'reservas_pasadas': reservas_pasadas,
            'promedio_horas': round(promedio_horas, 1),
            'crecimiento_porcentaje': round(crecimiento_porcentaje, 1),
            'proximas_reservas': proximas_reservas,
            'tipos_espacios': tipos_espacios,
            
            # COMPARATIVAS
            'horas_mes_anterior': int(horas_mes_anterior),
            'mejora_vs_anterior': horas_este_mes > horas_mes_anterior,
        }
        
        return render(request, 'reservas/mis_reservas.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar información: {str(e)}')
        return redirect('login')

@require_GET
@login_required
def verificar_disponibilidad_ajax(request):
    """
    Vista AJAX para verificar disponibilidad de horarios en tiempo real
    """
    espacio_id = request.GET.get('espacio_id')
    fecha = request.GET.get('fecha')
    
    if not espacio_id or not fecha:
        return JsonResponse({'error': 'Parámetros faltantes'}, status=400)
    
    try:
        espacio = Espacio.objects.get(id=espacio_id)
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        
        # Obtener todas las reservas existentes para ese espacio y fecha
        reservas_existentes = Reserva.objects.filter(
            espacio=espacio,
            fecha=fecha_obj
        ).values('hora_inicio', 'hora_fin')
        
        # Generar horarios según tipo de espacio
        horarios_disponibles = generar_horarios_por_tipo(espacio.tipo)
        
        # Marcar horarios ocupados
        for horario in horarios_disponibles:
            horario['ocupado'] = False
            hora_inicio_horario = datetime.strptime(horario['inicio'], '%H:%M').time()
            hora_fin_horario = datetime.strptime(horario['fin'], '%H:%M').time()
            
            # Verificar si hay conflicto con alguna reserva existente
            for reserva in reservas_existentes:
                if (hora_inicio_horario < reserva['hora_fin'] and 
                    hora_fin_horario > reserva['hora_inicio']):
                    horario['ocupado'] = True
                    break
        
        return JsonResponse({
            'horarios': horarios_disponibles,
            'tipo_espacio': espacio.tipo,
            'nombre_espacio': espacio.nombre
        })
        
    except Espacio.DoesNotExist:
        return JsonResponse({'error': 'Espacio no encontrado'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def generar_horarios_por_tipo(tipo_espacio):
    """
    Genera los horarios disponibles según el tipo de espacio
    """
    if 'directorio' in tipo_espacio.lower():
        return [
            {'inicio': '08:00', 'fin': '09:00', 'label': '8:00 AM - 9:00 AM'},
            {'inicio': '09:00', 'fin': '10:00', 'label': '9:00 AM - 10:00 AM'},
            {'inicio': '10:00', 'fin': '11:00', 'label': '10:00 AM - 11:00 AM'},
            {'inicio': '11:00', 'fin': '12:00', 'label': '11:00 AM - 12:00 PM'},
            {'inicio': '12:00', 'fin': '13:00', 'label': '12:00 PM - 1:00 PM'},
            {'inicio': '13:00', 'fin': '14:00', 'label': '1:00 PM - 2:00 PM'},
            {'inicio': '14:00', 'fin': '15:00', 'label': '2:00 PM - 3:00 PM'},
            {'inicio': '15:00', 'fin': '16:00', 'label': '3:00 PM - 4:00 PM'},
            {'inicio': '16:00', 'fin': '17:00', 'label': '4:00 PM - 5:00 PM'},
            {'inicio': '17:00', 'fin': '18:00', 'label': '5:00 PM - 6:00 PM'},
            {'inicio': '18:00', 'fin': '19:00', 'label': '6:00 PM - 7:00 PM'}
        ]
    elif 'estacionamiento' in tipo_espacio.lower():
        return [
            {'inicio': '07:00', 'fin': '08:00', 'label': '7:00 AM - 8:00 AM'},
            {'inicio': '08:00', 'fin': '09:00', 'label': '8:00 AM - 9:00 AM'},
            {'inicio': '09:00', 'fin': '10:00', 'label': '9:00 AM - 10:00 AM'},
            {'inicio': '10:00', 'fin': '11:00', 'label': '10:00 AM - 11:00 AM'},
            {'inicio': '11:00', 'fin': '12:00', 'label': '11:00 AM - 12:00 PM'},
            {'inicio': '12:00', 'fin': '13:00', 'label': '12:00 PM - 1:00 PM'},
            {'inicio': '13:00', 'fin': '14:00', 'label': '1:00 PM - 2:00 PM'},
            {'inicio': '14:00', 'fin': '15:00', 'label': '2:00 PM - 3:00 PM'},
            {'inicio': '15:00', 'fin': '16:00', 'label': '3:00 PM - 4:00 PM'},
            {'inicio': '16:00', 'fin': '17:00', 'label': '4:00 PM - 5:00 PM'},
            {'inicio': '17:00', 'fin': '18:00', 'label': '5:00 PM - 6:00 PM'}
        ]
    
    elif 'terraza' in tipo_espacio.lower():
        return [
            {'inicio': '15:00', 'fin': '16:00', 'label': '3:00 PM - 4:00 PM'},
            {'inicio': '16:00', 'fin': '17:00', 'label': '4:00 PM - 5:00 PM'},
            {'inicio': '17:00', 'fin': '18:00', 'label': '5:00 PM - 6:00 PM'},
            {'inicio': '18:00', 'fin': '19:00', 'label': '6:00 PM - 7:00 PM'},
            {'inicio': '19:00', 'fin': '20:00', 'label': '7:00 PM - 8:00 PM'},
            {'inicio': '20:00', 'fin': '21:00', 'label': '8:00 PM - 9:00 PM'},
            {'inicio': '21:00', 'fin': '22:00', 'label': '9:00 PM - 10:00 PM'},
            ]
    
    elif 'comedor' in tipo_espacio.lower():
        return [
        {'inicio': '8:00', 'fin': '9:00', 'label': '8:00 AM - 9:00 AM'},
        {'inicio': '9:00', 'fin': '10:00', 'label': '9:00 AM - 10:00 AM'},
        {'inicio': '10:00', 'fin': '11:00', 'label': '10:00 AM - 11:00 AM'},
    ]

    else:  # salas
        return [
            {'inicio': '08:00', 'fin': '09:00', 'label': '8:00 AM - 9:00 AM'},
            {'inicio': '09:00', 'fin': '10:00', 'label': '9:00 AM - 10:00 AM'},
            {'inicio': '10:00', 'fin': '11:00', 'label': '10:00 AM - 11:00 AM'},
            {'inicio': '11:00', 'fin': '12:00', 'label': '11:00 AM - 12:00 PM'},
            {'inicio': '12:00', 'fin': '13:00', 'label': '12:00 PM - 1:00 PM'},
            {'inicio': '13:00', 'fin': '14:00', 'label': '1:00 PM - 2:00 PM'},
            {'inicio': '14:00', 'fin': '15:00', 'label': '2:00 PM - 3:00 PM'},
            {'inicio': '15:00', 'fin': '16:00', 'label': '3:00 PM - 4:00 PM'},
            {'inicio': '16:00', 'fin': '17:00', 'label': '4:00 PM - 5:00 PM'},
            {'inicio': '17:00', 'fin': '18:00', 'label': '5:00 PM - 6:00 PM'}
            
        ]

@require_GET
@login_required
def obtener_calendario_ocupacion_ajax(request):
    """
    Vista AJAX para obtener datos de ocupación del calendario
    """
    espacio_id = request.GET.get('espacio_id')
    mes = request.GET.get('mes')  # formato: YYYY-MM
    
    if not espacio_id:
        return JsonResponse({'error': 'ID de espacio requerido'}, status=400)
    
    try:
        espacio = Espacio.objects.get(id=espacio_id)
        
        # Si no se especifica mes, usar el actual
        if mes:
            year, month = map(int, mes.split('-'))
        else:
            hoy = date.today()
            year, month = hoy.year, hoy.month
        
        # Obtener primer y último día del mes
        primer_dia = date(year, month, 1)
        if month == 12:
            ultimo_dia = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(year, month + 1, 1) - timedelta(days=1)
        
        # Obtener todas las reservas del mes
        reservas_mes = Reserva.objects.filter(
            espacio=espacio,
            fecha__gte=primer_dia,
            fecha__lte=ultimo_dia
        ).values('fecha').annotate(
            total_reservas=Count('id')
        )
        
        # Convertir a diccionario para fácil acceso
        ocupacion_por_dia = {
            str(reserva['fecha']): reserva['total_reservas'] 
            for reserva in reservas_mes
        }
        
        return JsonResponse({
            'ocupacion_por_dia': ocupacion_por_dia,
            'mes_solicitado': f"{year}-{month:02d}",
            'espacio_nombre': espacio.nombre
        })
        
    except Espacio.DoesNotExist:
        return JsonResponse({'error': 'Espacio no encontrado'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Formato de mes inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ===== VISTA ORIGINAL MODIFICADA =====

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
            
            # Validar límites según tipo de espacio
            if espacio.tipo.lower() in ['sala'] and len(bloques_horarios) > 8:
                messages.error(request, 'Las salas permiten máximo 8 bloques por día')
                return redirect('nueva_reserva')
            elif 'directorio' in espacio.tipo.lower():
                if len(bloques_horarios) < 2:
                    messages.error(request, 'El directorio requiere mínimo 2 bloques de horario')
                    return redirect('nueva_reserva')
                elif len(bloques_horarios) > 8:
                    messages.error(request, 'El directorio permite máximo 8 bloques por día')
                    return redirect('nueva_reserva')
            
            reservas_creadas = 0
            
            for bloque in bloques_horarios:
                if '-' not in bloque:
                    continue
                    
                try:
                    hora_inicio_str, hora_fin_str = bloque.split('-')
                    hora_inicio_obj = datetime.strptime(hora_inicio_str, '%H:%M').time()
                    hora_fin_obj = datetime.strptime(hora_fin_str, '%H:%M').time()
                    
                    # Verificar conflictos (doble verificación en backend)
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
            Q(tipo__in=['sala', 'directorio', 'terraza', 'comedor']) |
            Q(tipo='estacionamiento', es_estacionamiento_visita=True) |
            Q(tipo='estacionamiento', oficina_propietaria=oficina)
        )
    )
    
    context = {
        'espacios': espacios,
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