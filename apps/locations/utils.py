"""
Utility functions for locations app
"""
import string
import secrets
from django.contrib.auth.hashers import make_password


def generate_polling_unit_password(length=5):
    """
    Generate a random password for polling units.
    Default 5 characters, can be up to 8 characters.
    
    Args:
        length: Password length (default 5, max 8)
    
    Returns:
        Plain text password string
    """
    if length < 5 or length > 8:
        length = 5
    
    # Use alphanumeric characters (uppercase + lowercase + digits)
    characters = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password


def hash_password(password):
    """Hash a plain text password using Django's password hasher"""
    return make_password(password)
