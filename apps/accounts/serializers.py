"""
Serializers for the accounts app - converts User model to/from JSON
"""
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_central_admin', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserDetailSerializer(UserSerializer):
    """Extended User serializer with more details"""
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LoginSerializer(serializers.Serializer):
    """Serializer for login - accepts email OR username and password"""
    email = serializers.CharField()  # Can be email or username
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email_or_username = data.get('email')
        password = data.get('password')

        if not email_or_username or not password:
            raise serializers.ValidationError("Email/username and password are required.")

        return data


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout - just acknowledges the action"""
    message = serializers.CharField(read_only=True)


class PollingUnitLoginSerializer(serializers.Serializer):
    """Serializer for polling unit login - accepts unit_id and password"""
    unit_id = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        unit_id = data.get('unit_id', '').strip().upper()
        password = data.get('password')

        if not unit_id or not password:
            raise serializers.ValidationError("Unit ID and password are required.")

        return {**data, 'unit_id': unit_id}
