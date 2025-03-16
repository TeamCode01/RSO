from rest_framework.permissions import BasePermission

from api.utils import check_commander_or_not
from headquarters.models import Detachment, LocalHeadquarter, EducationalHeadquarter, RegionalHeadquarter, \
    DistrictHeadquarter


class IsDetachmentCommander(BasePermission):
    def has_permission(self, request, view):
        return check_commander_or_not(request, (Detachment,))


class IsLocalCommanderOrLower(BasePermission):
    def has_permission(self, request, view):
        return check_commander_or_not(request, (Detachment, EducationalHeadquarter, LocalHeadquarter))


class IsEducationalCommanderOrLower(BasePermission):
    def has_permission(self, request, view):
        return check_commander_or_not(request, (Detachment, EducationalHeadquarter))


class IsRegionalCommanderOrLower(BasePermission):
    def has_permission(self, request, view):
        return check_commander_or_not(
            request, (Detachment, EducationalHeadquarter, LocalHeadquarter, RegionalHeadquarter)
        )


class IsDistrictCommanderOrLower(BasePermission):
    def has_permission(self, request, view):
        return check_commander_or_not(
            request, (
                Detachment, EducationalHeadquarter, LocalHeadquarter, RegionalHeadquarter, DistrictHeadquarter
            )
        )


class IsCentralCommanderOrLower(BasePermission):
    def has_permission(self, request, view):
        return check_commander_or_not(
            request, (
                Detachment, EducationalHeadquarter, LocalHeadquarter, RegionalHeadquarter, DistrictHeadquarter
            )
        )
