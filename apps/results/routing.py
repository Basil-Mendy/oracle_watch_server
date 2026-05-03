"""
Django Channels routing for WebRTC signaling
Maps WebSocket URLs to consumers
"""

from django.urls import re_path
from apps.results.consumers import LiveStreamConsumer

# WebSocket URL patterns
websocket_urlpatterns = [
    re_path(r'ws/live-stream/$', LiveStreamConsumer.as_asgi()),
]
