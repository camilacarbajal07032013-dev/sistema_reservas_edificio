# Usar imagen base de Python
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema para PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Recolectar archivos estáticos (esto SÍ se puede hacer en build porque no necesita DB)
RUN python manage.py collectstatic --noinput

# Exponer el puerto
EXPOSE $PORT

# Comando de inicio: aquí SÍ ejecutamos migrate porque ya hay conexión a DB
CMD python manage.py migrate && gunicorn edificio.wsgi:application --bind 0.0.0.0:${PORT:-8000}