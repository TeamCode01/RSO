from headquarters.models import RegionalHeadquarter
from rest_framework import permissions


class IsRegionalCommander(permissions.BasePermission):
    """Использовать для моделей со ссылкой на regional_headquarter."""

    def has_permission(self, request, view):
        try:
            RegionalHeadquarter.objects.get(commander=request.user)
            return True
        except RegionalHeadquarter.DoesNotExist:
            return True if request.method in permissions.SAFE_METHODS else False

    def has_object_permission(self, request, view, obj):
        return (
                obj.regional_headquarter.commander == request.user or
                request.method in permissions.SAFE_METHODS
        )
