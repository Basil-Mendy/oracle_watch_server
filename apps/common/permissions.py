"""
Shared utilities and permissions for all apps.
"""
from rest_framework import permissions


class IsCentralAdmin(permissions.BasePermission):
    """
    Permission to check if user is a central admin.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and getattr(request.user, 'is_central_admin', False)


class IsPollingUnit(permissions.BasePermission):
    """
    Permission to check if the request is from a valid polling unit.
    """
    def has_permission(self, request, view):
        # Will implement polling unit authentication
        return True
