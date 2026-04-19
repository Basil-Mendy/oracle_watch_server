"""
Views for user authentication
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from .serializers import LoginSerializer, LogoutSerializer, UserSerializer, PollingUnitLoginSerializer
from .models import User


@api_view(['POST'])
@permission_classes([AllowAny])
def LoginView(request):
    """
    Login endpoint - accepts email OR username and password, returns user data and token
    
    POST /api/auth/login/
    {
        "email": "admin@example.com",  (or username: "admin")
        "password": "password123"
    }
    
    Returns:
    {
        "user": {
            "id": "uuid",
            "email": "admin@example.com",
            "username": "admin",
            "first_name": "Admin",
            "last_name": "User",
            "is_central_admin": true,
            "created_at": "2024-01-01T00:00:00Z"
        },
        "token": "auth_token_string",
        "message": "Login successful"
    }
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email_or_username = serializer.validated_data['email']
    password = serializer.validated_data['password']

    # Try to get user by email first, then by username
    user = None
    try:
        # First try email
        user = User.objects.get(email=email_or_username)
    except User.DoesNotExist:
        try:
            # Then try username
            user = User.objects.get(username=email_or_username)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email/username or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

    # Check password
    if not user.check_password(password):
        return Response(
            {"error": "Invalid email/username or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"error": "User account is inactive"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Generate or get token
    from rest_framework.authtoken.models import Token
    token, created = Token.objects.get_or_create(user=user)

    user_serializer = UserSerializer(user)
    return Response({
        "user": user_serializer.data,
        "token": token.key,
        "message": "Login successful"
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def LogoutView(request):
    """
    Logout endpoint - invalidates user's current token
    
    POST /api/auth/logout/
    Headers: Authorization: Token <token>
    
    Returns:
    {
        "message": "Logout successful"
    }
    """
    # Delete the user's token
    from rest_framework.authtoken.models import Token
    try:
        token = Token.objects.get(user=request.user)
        token.delete()
    except Token.DoesNotExist:
        pass

    return Response(
        {"message": "Logout successful"},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def PollingUnitLoginView(request):
    """
    Polling Unit login endpoint - accepts unit_id and password, returns polling unit data and token
    
    POST /api/auth/polling-unit-login/
    {
        "unit_id": "PU-00001",
        "password": "password123"
    }
    
    Returns:
    {
        "polling_unit": {
            "id": "uuid",
            "unit_id": "PU-00001",
            "name": "Primary School A",
            "ward": "uuid",
            "ward_name": "Ward 1",
            "lga": "uuid",
            "lga_name": "Aba North",
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z"
        },
        "token": "auth_token_string",
        "message": "Polling unit login successful"
    }
    """
    serializer = PollingUnitLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    unit_id = serializer.validated_data['unit_id'].upper()
    password = serializer.validated_data['password']

    # Import PollingUnit here to avoid circular imports
    from apps.locations.models import PollingUnit
    from apps.locations.serializers import PollingUnitSerializer
    from rest_framework.authtoken.models import Token

    try:
        polling_unit = PollingUnit.objects.get(unit_id=unit_id)
    except PollingUnit.DoesNotExist:
        return Response(
            {"error": "Invalid Polling Unit ID or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not polling_unit.is_active:
        return Response(
            {"error": "This polling unit is inactive"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Check password - assuming password is stored hashed
    from django.contrib.auth.hashers import check_password
    if not check_password(password, polling_unit.password):
        return Response(
            {"error": "Invalid Polling Unit ID or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Generate a pseudo-token for polling unit (not tied to User model)
    # We'll use the polling unit ID as the basis for the token
    import hashlib
    import uuid
    token_string = hashlib.sha256(
        f"{polling_unit.id}{password}".encode()
    ).hexdigest()

    # Store this token in a cache or session for validation
    from django.core.cache import cache
    cache.set(f"pu_token_{token_string}", {
        "unit_id": polling_unit.unit_id,
        "polling_unit_id": str(polling_unit.id),
    }, 86400 * 7)  # Valid for 7 days

    pu_serializer = PollingUnitSerializer(polling_unit)
    return Response({
        "polling_unit": pu_serializer.data,
        "token": token_string,
        "message": "Polling unit login successful"
    }, status=status.HTTP_200_OK)
