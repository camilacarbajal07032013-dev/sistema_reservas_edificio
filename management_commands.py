import os
import django
from django.contrib.auth.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edificio.settings')
django.setup()

# Crear superusuario si no existe
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@edificio.com', 'admin123')
    print("Superusuario admin creado exitosamente")

# Crear usuario oficina301 si no existe
if not User.objects.filter(username='oficina301').exists():
    user = User.objects.create_user('oficina301', password='edificio2025')
    print("Usuario oficina301 creado exitosamente")