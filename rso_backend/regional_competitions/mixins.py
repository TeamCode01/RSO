from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)
from rest_framework.viewsets import GenericViewSet


class RegionalRMixin(RetrieveModelMixin, ListModelMixin, CreateModelMixin, GenericViewSet):
    pass


class RegionalRMeMixin(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    pass


class RetrieveCreateMixin(RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    pass
