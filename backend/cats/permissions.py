from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.owner_id == request.user.pk


class AchievementPermission(BasePermission):
    """Users may add shared names; only staff may edit/delete the shared dictionary."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated) and (
            request.method in SAFE_METHODS or request.method == 'POST' or request.user.is_staff
        )
