release: python management_commands.py && python manage.py migrate
web: gunicorn edificio.wsgi:application --bind 0.0.0.0:$PORT