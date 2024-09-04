from django.db.models import Q
from django_filters.filters import BooleanFilter, CharFilter, NumberFilter
from django_filters.rest_framework import FilterSet

from regional_competitions.models import StatisticalRegionalReport


class StatisticalRegionalReportFilter(FilterSet):
    district_id = CharFilter(method='filter_by_district_name')
    regional_headquarter_name = CharFilter(method='filter_by_regional_headquarter_name')

    class Meta:
        model = StatisticalRegionalReport
        fields = ['district_id', 'regional_headquarter_name']

    def filter_by_district_name(self, queryset, name, value):
        return queryset.filter(regional_headquarter__district_headquarter_id=value)

    def filter_by_regional_headquarter_name(self, queryset, name, value):
        return queryset.filter(regional_headquarter__name__icontains=value)
