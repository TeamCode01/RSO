from django.http import Http404
from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)
from rest_framework.viewsets import GenericViewSet

from headquarters.models import RegionalHeadquarter
from regional_competitions.utils import get_report_number_by_class_name


class RegionalRMixin(RetrieveModelMixin, CreateModelMixin, GenericViewSet):

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get('pk')
        objects = queryset.filter(regional_headquarter_id=pk)
        if objects.exists():
            latest_object = objects.order_by('-id')[0]
            return latest_object
        raise Http404("Страница не найдена")

    def get_report_number(self):
        return get_report_number_by_class_name(self)

    def perform_create(self, serializer):
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))

    def perform_update(self, request, serializer):
        serializer.save(regional_headquarter=RegionalHeadquarter.objects.get(commander=self.request.user))


class RegionalRMeMixin(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    pass


class ListRetrieveCreateMixin(RetrieveModelMixin, CreateModelMixin, ListModelMixin, GenericViewSet):
    pass
