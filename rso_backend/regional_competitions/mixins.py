from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)
from rest_framework.viewsets import GenericViewSet


class RegionalRMixin(RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    pass


class RegionalRMeMixin(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    pass


class ListRetrieveCreateMixin(RetrieveModelMixin, CreateModelMixin, ListModelMixin, GenericViewSet):
    pass
