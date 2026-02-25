from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Object-level permission: only the owner can access."""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission: owner can edit, others can only read."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """Allow admins full access, others read-only."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
