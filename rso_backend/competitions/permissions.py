from rest_framework.permissions import BasePermission
from django.conf import settings
from headquarters.models import Detachment, UserRegionalHeadquarterPosition


class IsRegionalCommanderOrCommissionerOfDetachment(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        detachment_pk = view.kwargs.get('detachment_pk')

        try:
            detachment = Detachment.objects.get(pk=detachment_pk)
        except Detachment.DoesNotExist:
            return False
        regional_headquarter = detachment.regional_headquarter

        if user == regional_headquarter.commander or UserRegionalHeadquarterPosition.objects.filter(
            headquarter=regional_headquarter,
            position__name=settings.COMMISSIONER_POSITION_NAME
        ).exists():
            return True

        return False
