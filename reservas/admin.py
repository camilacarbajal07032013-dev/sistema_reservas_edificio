from django.contrib import admin
from .models import Oficina, Espacio, Reserva

@admin.register(Oficina)
class OficinaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nombre_empresa', 'user']
    search_fields = ['numero', 'nombre_empresa']

@admin.register(Espacio)
class EspacioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'activo']
    list_filter = ['tipo', 'activo']
    search_fields = ['nombre']

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['oficina', 'espacio', 'fecha', 'hora_inicio', 'hora_fin', 'duracion_horas']
    list_filter = ['fecha', 'espacio__tipo']
    search_fields = ['oficina__numero', 'espacio__nombre']
    date_hierarchy = 'fecha'
    
    def duracion_horas(self, obj):
        return f"{obj.duracion_horas()}h"
    duracion_horas.short_description = 'Duración'