"""
Custom authentication backends for DRF
"""
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser


class PollingUnitUser(AnonymousUser):
    """
    Mock user object for polling units.
    Inherits from AnonymousUser with overridden properties for authentication.
    """
    def __init__(self, polling_unit_id, unit_id):
        super().__init__()
        self.polling_unit_id = polling_unit_id
        self.unit_id = unit_id
        self._is_authenticated = True
        self._is_active = True

    @property
    def is_authenticated(self):
        """Override the read-only property to return True for polling unit users"""
        return self._is_authenticated

    @property
    def is_active(self):
        """Override the read-only property to return True for polling unit users"""
        return self._is_active


class PollingUnitTokenAuthentication(TokenAuthentication):
    """
    Custom authentication that extends DRF's TokenAuthentication
    to also validate polling unit tokens stored in cache.
    """
    
    def authenticate(self, request):
        # Try standard DRF token authentication first
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            pass
        except TypeError:
            # super().authenticate() returns None if no token found
            pass
        
        # If DRF auth fails or no token, check for polling unit token in cache
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        
        if len(auth) != 2 or auth[0].lower() != 'token':
            return None
        
        token = auth[1]
        
        # Check if this is a polling unit token in cache
        cache_key = f"pu_token_{token}"
        pu_data = cache.get(cache_key)
        
        if not pu_data:
            # Token not found in cache and not a valid DRF token
            return None
        
        # Create a mock polling unit user object for authenticated requests
        user = PollingUnitUser(
            polling_unit_id=pu_data.get('polling_unit_id'),
            unit_id=pu_data.get('unit_id')
        )
        
        return (user, token)
