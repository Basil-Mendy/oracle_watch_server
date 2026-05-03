"""
ASGI config for Oracle-Watch project.
Uses Django Channels for WebSocket support (real-time live streaming)
"""
import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oracle_watch.settings')

# Setup Django first
django.setup()

# Import routing AFTER Django setup
from apps.results.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # HTTP requests (standard Django)
    'http': get_asgi_application(),
    
    # WebSocket connections (Channels)
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
