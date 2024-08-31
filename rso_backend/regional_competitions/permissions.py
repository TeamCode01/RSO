from headquarters.models import CentralHeadquarter, RegionalHeadquarter
from rest_framework import permissions

from regional_competitions.models import ExpertRole


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


class IsCentralHeadquarterExpert(permissions.BasePermission):
    """
    Проверка, является ли пользователь экспертом центрального штаба или
    командиром центрального штаба.
    """

    def has_permission(self, request, view):
        if request.user.is_authenticated and (
            ExpertRole.objects.filter(
                user=request.user, central_headquarter__isnull=False
            ).exists() or CentralHeadquarter.objects.filter(
                commander=request.user
            ).exists()
        ):
            return True


class IsDistrictHeadquarterExpert(permissions.BasePermission):
    """Проверка, является ли пользователь экспертом окружного штаба."""

    def has_permission(self, request, view):
        if request.user.is_authenticated and ExpertRole.objects.filter(
            user=request.user, district_headquarter__isnull=False
        ).exists():
            return True

    def has_object_permission(self, request, view, obj):
        """
        Проверяет, является ли пользователь экспертом окружного штаба,
        у которого есть права на доступ к верификации отчетов этого региона.

        Является ли рег штаб подчиненным этого окружного штаба.
        """
        if request.user.is_authenticated:
            obj_district_headquarter_id = obj.regional_headquarter.district_headquarter_id
            return ExpertRole.objects.filter(
                user=request.user, district_headquarter_id=obj_district_headquarter_id
            ).exists()


class IsCentralOrDistrictHeadquarterExpert(permissions.BasePermission):
    """
    Проверка, является ли пользователь экспертом центрального или окружного штаба.

    Для вывода списка отправленных на проверку отчетов по 2 части (api_view).
    """

    def has_permission(self, request, view):
        if request.user.is_authenticated and (
            ExpertRole.objects.filter(
                user=request.user, central_headquarter__isnull=False
            ).exists() or ExpertRole.objects.filter(
                user=request.user, district_headquarter__isnull=False
            ).exists()
        ):
            return True


class IsRegionalCommanderAuthorOrCentralHeadquarterExpert(permissions.BasePermission):
    """
    Проверка, является ли пользователь командиром рег штаба, который является
    автором отчета или экспертом центрального штаба.

    Только для доступа к объекту.
    Для retrieve 1 части отчета.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated:
            return (
                    request.user == obj.regional_headquarter.commander or
                    ExpertRole.objects.filter(
                        user=request.user, central_headquarter__isnull=False
                    ).exists()
            )
