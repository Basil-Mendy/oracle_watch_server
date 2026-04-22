web: gunicorn oracle_watch.wsgi --timeout 120
release: python manage.py migrate && python manage.py collectstatic --noinput