from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)
from rest_framework.viewsets import GenericViewSet

from regional_competitions.constants import CONVERT_TO_MB, ROUND_2_SIGNS


class RegionalRMixin(RetrieveModelMixin, ListModelMixin, CreateModelMixin, GenericViewSet):
    pass


class RegionalRMeMixin(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    pass
