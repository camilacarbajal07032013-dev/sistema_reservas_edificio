[phases.setup]
nixPkgs = ['python311', 'postgresql_16.dev', 'gcc']

[phases.install]
cmds = ['python -m venv --copies /opt/venv && . /opt/venv/bin/activate && pip install -r requirements.txt']

[phases.build]
cmds = ['pip install -r requirements.txt']

[start]
cmd = 'python manage.py migrate && python manage.py collectstatic --noinput && gunicorn edificio.wsgi:application --bind 0.0.0.0:$PORT'