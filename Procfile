release: python create_admin.py && python manage.py collectstatic --noinput && python manage.py migrate
web: gunicorn edificio.wsgi:application --bind 0.0.0.0:$PORT