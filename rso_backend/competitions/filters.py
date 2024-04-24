from django.db.models import Q
from django_filters.rest_framework import FilterSet
from django_filters.filters import BooleanFilter, CharFilter, NumberFilter

from .models import CompetitionParticipants, QVerificationLog


class CompetitionParticipantsFilter(FilterSet):
    is_tandem = BooleanFilter(method='filter_by_group')
    area = CharFilter(method='filter_by_area')

    class Meta:
        model = CompetitionParticipants
        fields = ['is_tandem', 'area']

    def filter_by_group(self, queryset, name, value):
        if value:
            return queryset.filter(detachment__isnull=False)
        else:
            return queryset.filter(detachment__isnull=True)

    def filter_by_area(self, queryset, name, value):
        return queryset.filter(
            Q(detachment__area__name=value) | Q(junior_detachment__area__name=value)
        )


class QVerificationLogFilter(FilterSet):
    q_number = NumberFilter()
    verifier_id = NumberFilter(field_name='verifier__id')
    verified_detachment_id = NumberFilter(field_name='verified_detachment__id')

    class Meta:
        model = QVerificationLog
        fields = ['q_number', 'verifier_id', 'verified_detachment_id']
