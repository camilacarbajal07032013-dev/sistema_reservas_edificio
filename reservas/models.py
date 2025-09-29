from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, date, time

class Oficina(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    numero = models.CharField(max_length=20)
    nombre_empresa = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.numero} - {self.nombre_empresa}"
    
class Espacio(models.Model):
    TIPOS = [
        ('sala', 'Sala'),
        ('directorio', 'Directorio'), 
        ('terraza', 'Terraza'),
        ('estacionamiento', 'Estacionamiento'),
        ('comedor', 'Comedor'),
    ]
    
    nombre = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    activo = models.BooleanField(default=True)
    
    # Campos que ya agregaste antes
    es_estacionamiento_visita = models.BooleanField(default=False)
    oficina_propietaria = models.ForeignKey(
        'Oficina', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='estacionamientos_propios',
        help_text="Oficina dueña de este estacionamiento"
    )
    
    # NUEVOS CAMPOS PARA HORARIOS ESPECÍFICOS - AGREGAR AQUÍ ⬇️
    horarios_personalizados = models.JSONField(
        default=list, 
        blank=True,
        help_text="Horarios específicos para este espacio"
    )
    usar_horarios_personalizados = models.BooleanField(
        default=False,
        help_text="Usar horarios específicos en lugar de horarios estándar"
    )
    
    def __str__(self):
        return self.nombre

class Reserva(models.Model):
    oficina = models.ForeignKey(Oficina, on_delete=models.CASCADE)
    espacio = models.ForeignKey(Espacio, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Para estacionamientos
    nombre_visitante = models.CharField(max_length=100, blank=True)
    placa_visitante = models.CharField(max_length=15, blank=True)
    empresa_visitante = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.oficina} - {self.espacio} - {self.fecha}"
    
    def duracion_horas(self):
        inicio = datetime.combine(date.today(), self.hora_inicio)
        fin = datetime.combine(date.today(), self.hora_fin)
        return (fin - inicio).seconds // 3600