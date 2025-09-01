web: python manage.py collectstatic --noinput && python manage.py migrate && gunicorn edificio.wsgi:application --bind 0.0.0.0:$PORT
