from django.db.models import Q
from django_filters import rest_framework as filters

from headquarters.models import (Detachment, EducationalHeadquarter,
                                 LocalHeadquarter, RegionalHeadquarter)


class RegionalHeadquarterFilter(filters.FilterSet):
    district_headquarter__name = filters.CharFilter(
        field_name='district_headquarter__name',
        lookup_expr='icontains',
        label='Название окружного штаба'
    )
    region = filters.CharFilter(
        field_name='region__name',
        lookup_expr='iexact',
        label='Название региона'
    )

    class Meta:
        model = RegionalHeadquarter
        fields = ('district_headquarter__name', 'region')


class LocalHeadquarterFilter(filters.FilterSet):
    district_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__district_headquarter__name',
        lookup_expr='icontains',
        label='Название окружного штаба'
    )
    regional_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__name',
        lookup_expr='icontains',
        label='Название регионального штаба'
    )

    class Meta:
        model = LocalHeadquarter
        fields = ('regional_headquarter__name', 'district_headquarter__name',)


class EducationalHeadquarterFilter(filters.FilterSet):

    district_headquarter__name = filters.CharFilter(
        method='filter_district_headquarter',
        label='Название окружного штаба'
    )
    regional_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__name',
        lookup_expr='icontains',
        label='Название регионального штаба'
    )
    local_headquarter__name = filters.CharFilter(
        field_name='local_headquarter__name',
        lookup_expr='icontains',
        label='Название местного штаба'
    )

    def filter_district_headquarter(self, queryset, name, value):
        return queryset.filter(
            Q(
                local_headquarter__regional_headquarter__district_headquarter__name__icontains=value
            ) |
            Q(
                regional_headquarter__district_headquarter__name__icontains=value
            )
        )

    class Meta:
        model = EducationalHeadquarter
        fields = (
            'local_headquarter__name',
            'regional_headquarter__name',
            'district_headquarter__name',
        )


class DetachmentFilter(filters.FilterSet):

    area__name = filters.CharFilter(
        field_name='area__name',
        lookup_expr='iexact',
        label='Название направления'
    )
    educational_institution__name = filters.CharFilter(
        field_name='educational_institution__name',
        lookup_expr='iexact',
        label='Название образовательной организации'
    )
    district_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__district_headquarter__name',
        lookup_expr='iexact',
        label='Название окружного штаба'
    )
    regional_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__name',
        lookup_expr='iexact',
        label='Название регионального штаба'
    )
    local_headquarter__name = filters.CharFilter(
        field_name='local_headquarter__name',
        lookup_expr='iexact',
        label='Название местного штаба'
    )
    educational_headquarter__name = filters.CharFilter(
        field_name='educational_headquarter__name',
        lookup_expr='iexact',
        label='Название образовательного штаба'
    )

    class Meta:
        model = Detachment
        fields = (
            'area__name',
            'educational_institution__name',
            'district_headquarter__name',
            'regional_headquarter__name',
            'local_headquarter__name',
            'educational_headquarter__name',
        )


class DetachmentListFilter(filters.FilterSet):

    district_headquarter__id = filters.CharFilter(
        field_name='regional_headquarter__district_headquarter__id',
        lookup_expr='iexact',
        label='id окружного штаба'
    )
    regional_headquarter__id = filters.CharFilter(
        field_name='regional_headquarter__id',
        lookup_expr='iexact',
        label='id регионального штаба'
    )
    local_headquarter__id = filters.CharFilter(
        field_name='local_headquarter__id',
        lookup_expr='iexact',
        label='id местного штаба'
    )
    educational_headquarter__id = filters.CharFilter(
        field_name='educational_headquarter__id',
        lookup_expr='iexact',
        label='id образовательного штаба'
    )
    district_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__district_headquarter__name',
        lookup_expr='iexact',
        label='Название окружного штаба'
    )
    regional_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__name',
        lookup_expr='iexact',
        label='Название регионального штаба'
    )
    local_headquarter__name = filters.CharFilter(
        field_name='local_headquarter__name',
        lookup_expr='iexact',
        label='Название местного штаба'
    )
    educational_headquarter__name = filters.CharFilter(
        field_name='educational_headquarter__name',
        lookup_expr='iexact',
        label='Название образовательного штаба'
    )

    class Meta:
        model = Detachment
        fields = (
            'district_headquarter__id',
            'regional_headquarter__id',
            'local_headquarter__id',
            'educational_headquarter__id',
            'district_headquarter__name',
            'regional_headquarter__name',
            'local_headquarter__name',
            'educational_headquarter__name',
        )


class SubCommanderListFilter(filters.FilterSet):
    central_headquarter__id = filters.CharFilter(
        field_name='central_headquarter__id',
        lookup_expr='iexact',
        label='id центрального штаба'
    )
    district_headquarter__id = filters.CharFilter(
        field_name='regional_headquarter__district_headquarter__id',
        lookup_expr='iexact',
        label='id окружного штаба'
    )
    regional_headquarter__id = filters.CharFilter(
        field_name='regional_headquarter__id',
        lookup_expr='iexact',
        label='id регионального штаба'
    )
    local_headquarter__id = filters.CharFilter(
        field_name='local_headquarter__id',
        lookup_expr='iexact',
        label='id местного штаба'
    )
    educational_headquarter__id = filters.CharFilter(
        field_name='educational_headquarter__id',
        lookup_expr='iexact',
        label='id образовательного штаба'
    )
    central_headquarter__name = filters.CharFilter(
        field_name='central_headquarter__name',
        lookup_expr='iexact',
        label='Название центрального штаба'
    )
    district_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__district_headquarter__name',
        lookup_expr='iexact',
        label='Название окружного штаба'
    )
    regional_headquarter__name = filters.CharFilter(
        field_name='regional_headquarter__name',
        lookup_expr='iexact',
        label='Название регионального штаба'
    )
    local_headquarter__name = filters.CharFilter(
        field_name='local_headquarter__name',
        lookup_expr='iexact',
        label='Название местного штаба'
    )
    educational_headquarter__name = filters.CharFilter(
        field_name='educational_headquarter__name',
        lookup_expr='iexact',
        label='Название образовательного штаба'
    )
    user_id = filters.NumberFilter(
        field_name='user_id',
        lookup_expr='exact'
        )
    first_name = filters.CharFilter(
        field_name='user__first_name',
          lookup_expr='icontains'
          )
    last_name = filters.CharFilter(
        field_name='user__last_name',
        lookup_expr='icontains'
        )
    patronymic_name = filters.CharFilter(
        field_name='user__patronymic_name', 
        lookup_expr='icontains'
        )

    class Meta:
        model = Detachment
        fields = (
            'central_headquarter__id',
            'district_headquarter__id',
            'regional_headquarter__id',
            'local_headquarter__id',
            'educational_headquarter__id',
            'central_headquarter__name',
            'district_headquarter__name',
            'regional_headquarter__name',
            'local_headquarter__name',
            'educational_headquarter__name',
            'user_id',
            'first_name',
            'last_name',
            'patronymic_name',
        )
