#!/bin/bash
set -e

echo "Waiting for Postgres to be ready..."

# Función para verificar si Postgres está listo
postgres_ready() {
python << END
import sys
import os

try:
    import dj_database_url
    db_config = dj_database_url.config(default=os.environ.get('DATABASE_URL'))
    
    import psycopg2
    conn = psycopg2.connect(
        dbname=db_config['NAME'],
        user=db_config['USER'],
        password=db_config['PASSWORD'],
        host=db_config['HOST'],
        port=db_config['PORT'],
        connect_timeout=5
    )
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(-1)
sys.exit(0)
END
}

# Intentar conectar hasta 30 veces (5 minutos)
until postgres_ready; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 10
done

>&2 echo "Postgres is up - executing command"

# Ejecutar migraciones
python manage.py migrate

# Iniciar gunicorn
exec gunicorn edificio.wsgi:application --bind 0.0.0.0:${PORT:-8000}