"""
WSGI config for Oracle-Watch project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oracle_watch.settings')
application = get_wsgi_application()
