"""
Utility functions shared across the application.
"""
import random
import string
from apps.locations.models import PollingUnit


def generate_polling_unit_password(length=12):
    """
    Generate a random password for a polling unit.
    
    Args:
        length: Length of the password (default: 12)
    
    Returns:
        A random password string
    """
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))


def encrypt_password(password):
    """
    Encrypt a plain text password.
    Using Django's make_password for consistency.
    """
    from django.contrib.auth.hashers import make_password
    return make_password(password)


def verify_polling_unit_credentials(unit_id, password):
    """
    Verify if the polling unit credentials are correct.
    
    Args:
        unit_id: The polling unit ID
        password: The provided password
    
    Returns:
        True if credentials are correct, False otherwise
    """
    from django.contrib.auth.hashers import check_password
    try:
        polling_unit = PollingUnit.objects.get(unit_id=unit_id)
        return check_password(password, polling_unit.password)
    except PollingUnit.DoesNotExist:
        return False
