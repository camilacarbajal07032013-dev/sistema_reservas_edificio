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
    
    from django.db.models import Avg, Sum
    from decimal import Decimal
    import json
    
    # Fechas para cálculos
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    hace_una_semana = hoy - timedelta(days=7)
    hace_dos_semanas = hoy - timedelta(days=14)
    mes_actual = hoy.replace(day=1)
    mes_anterior = (mes_actual - timedelta(days=1)).replace(day=1)
    
    # Cálculos existentes...
    total_reservas = Reserva.objects.count()
    reservas_hoy = Reserva.objects.filter(fecha=hoy).count()
    
    # DATOS PARA GRÁFICOS
    
    # 1. Datos para gráfico semanal (últimos 7 días)
    datos_semana = []
    labels_semana = []
    for i in range(6, -1, -1):  # Últimos 7 días
        fecha_dia = hoy - timedelta(days=i)
        reservas_dia = Reserva.objects.filter(fecha=fecha_dia)
        horas_dia = sum([r.duracion_horas() for r in reservas_dia])
        
        datos_semana.append(horas_dia)
        labels_semana.append(fecha_dia.strftime('%a'))  # Lun, Mar, etc.
    
    # 2. Datos para gráfico de oficinas (top 5)
    oficinas_data = Reserva.objects.values(
        'oficina__numero', 'oficina__nombre_empresa'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    labels_oficinas = []
    datos_oficinas = []
    colores_oficinas = ['#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#95a5a6']
    
    for oficina in oficinas_data:
        labels_oficinas.append(f"Oficina {oficina['oficina__numero']}")
        datos_oficinas.append(oficina['total'])
    
    # Si hay menos de 5 oficinas, rellenar con 0s
    while len(datos_oficinas) < 5:
        labels_oficinas.append('Sin datos')
        datos_oficinas.append(0)
    
    # 3. OFICINAS CON DATOS REALES
    oficinas_activas = []
    for oficina in Oficina.objects.annotate(total_reservas=Count('reserva')).order_by('-total_reservas')[:10]:
        # Calcular horas totales para esta oficina
        reservas_oficina = Reserva.objects.filter(oficina=oficina)
        horas_totales_oficina = sum([r.duracion_horas() for r in reservas_oficina])
        
        # Calcular promedio por reserva
        if oficina.total_reservas > 0:
            promedio_por_reserva = horas_totales_oficina / oficina.total_reservas
        else:
            promedio_por_reserva = 0
        
        # Determinar uso principal
        tipos_uso = reservas_oficina.values('espacio__tipo').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        uso_principal = tipos_uso['espacio__tipo'] if tipos_uso else 'N/A'
        
        # Calcular eficiencia (ejemplo: % del objetivo mensual de 20 reservas)
        objetivo_mensual = 20
        eficiencia = min((oficina.total_reservas / objetivo_mensual) * 100, 100) if objetivo_mensual > 0 else 0
        
        # Calcular tendencia (comparar con mes anterior)
        reservas_mes_anterior_oficina = Reserva.objects.filter(
            oficina=oficina,
            fecha__gte=mes_anterior,
            fecha__lt=mes_actual
        ).count()
        
        if reservas_mes_anterior_oficina > 0:
            tendencia = ((oficina.total_reservas - reservas_mes_anterior_oficina) / reservas_mes_anterior_oficina) * 100
        else:
            tendencia = 100 if oficina.total_reservas > 0 else 0
        
        oficinas_activas.append({
            'oficina': oficina,
            'total_reservas': oficina.total_reservas,
            'horas_totales': round(horas_totales_oficina, 1),
            'promedio_por_reserva': round(promedio_por_reserva, 1),
            'uso_principal': uso_principal.title(),
            'eficiencia': round(eficiencia, 0),
            'tendencia': round(tendencia, 1)
        })
    
    # Resto de cálculos existentes...
    reservas_mes_actual = Reserva.objects.filter(fecha__gte=mes_actual, fecha__lte=hoy).count()
    reservas_mes_anterior = Reserva.objects.filter(fecha__gte=mes_anterior, fecha__lt=mes_actual).count()
    
    if reservas_mes_anterior > 0:
        crecimiento_mensual = ((reservas_mes_actual - reservas_mes_anterior) / reservas_mes_anterior) * 100
    else:
        crecimiento_mensual = 100 if reservas_mes_actual > 0 else 0
    
    # ... otros cálculos existentes
    
    context = {
        'total_reservas': total_reservas,
        'reservas_hoy': reservas_hoy,
        'crecimiento_mensual': round(crecimiento_mensual, 1),
        # ... otros campos existentes
        
        # NUEVOS DATOS PARA GRÁFICOS
        'chart_data': {
            'semana': {
                'labels': json.dumps(labels_semana),
                'data': json.dumps(datos_semana)
            },
            'oficinas': {
                'labels': json.dumps(labels_oficinas),
                'data': json.dumps(datos_oficinas),
                'colors': json.dumps(colores_oficinas)
            }
        },
        'oficinas_detalladas': oficinas_activas,
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
            
            # NUEVA VALIDACIÓN: Restricción de 30 minutos antes
            ahora = datetime.now()
            hoy = ahora.date()
            
            # Solo aplicar restricción si la reserva es para hoy
            if fecha_obj == hoy:
                hora_limite = ahora + timedelta(minutes=30)
                
                for bloque in bloques_horarios:
                    if '-' not in bloque:
                        continue
                    
                    try:
                        hora_inicio_str, hora_fin_str = bloque.split('-')
                        hora_inicio_obj = datetime.strptime(hora_inicio_str, '%H:%M').time()
                        
                        # Combinar fecha de hoy con la hora de inicio del bloque
                        datetime_inicio = datetime.combine(fecha_obj, hora_inicio_obj)
                        
                        # Verificar si el bloque inicia en menos de 30 minutos
                        if datetime_inicio <= hora_limite:
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