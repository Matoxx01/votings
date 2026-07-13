web: python manage.py collectstatic --noinput && gunicorn votings_project.wsgi:application --bind 0.0.0.0:$PORT --timeout 300
release: python manage.py migrate