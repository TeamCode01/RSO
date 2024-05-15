from django_filters import rest_framework as filters
from django.db.models import Q
from users.models import RSOUser


class RSOUserFilter(filters.FilterSet):
    date_of_birth = filters.DateFilter()
    date_of_birth_gte = filters.DateFilter(
        field_name='date_of_birth', lookup_expr='gte'
    )
    date_of_birth_lte = filters.DateFilter(
        field_name='date_of_birth', lookup_expr='lte'
    )
    district_headquarter__name = filters.CharFilter(
        field_name='userdistrictheadquarterposition__headquarter__name',
        lookup_expr='icontains',
        label='Название окружного штаба'
    )
    regional_headquarter__name = filters.CharFilter(
        field_name='userregionalheadquarterposition__headquarter__name',
        lookup_expr='icontains',
        label='Название регионального штаба'
    )
    local_headquarter__name = filters.CharFilter(
        field_name='userlocalheadquarterposition__headquarter__name',
        lookup_expr='icontains',
        label='Название местного штаба'
    )
    educational_headquarter__name = filters.CharFilter(
        field_name='usereducationalheadquarterposition__headquarter__name',
        lookup_expr='icontains',
        label='Название образовательного штаба'
    )
    detachment__name = filters.CharFilter(
        field_name='userdetachmentposition__headquarter__name',
        lookup_expr='icontains',
        label='Название отряда'
    )
    region = filters.CharFilter(
        field_name='region__name',
        lookup_expr='icontains',
        label='Регион'
    )

    class Meta:
        model = RSOUser
        fields = (
            'date_of_birth',
            'date_of_birth_gte',
            'date_of_birth_lte',
            'district_headquarter__name',
            'regional_headquarter__name',
            'local_headquarter__name',
            'educational_headquarter__name',
            'detachment__name',
            'gender',
            'is_verified',
            'membership_fee',
            'region',
        )

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        district_name = self.data.get('district_headquarter__name')
        regional_name = self.data.get('regional_headquarter__name')
        local_name = self.data.get('local_headquarter__name')
        educational_name = self.data.get('educational_headquarter__name')
        detachment_name = self.data.get('detachment__name')

        if district_name:
            queryset = queryset.filter(
                Q(userdistrictheadquarterposition__headquarter__name__icontains=district_name) |
                Q(userdistrictheadquarterposition__headquarter__commander__name__icontains=district_name)
            )

        if regional_name:
            queryset = queryset.filter(
                Q(userregionalheadquarterposition__headquarter__name__icontains=regional_name) |
                Q(userregionalheadquarterposition__headquarter__commander__name__icontains=regional_name)
            )

        if local_name:
            queryset = queryset.filter(
                Q(userlocalheadquarterposition__headquarter__name__icontains=local_name) |
                Q(userlocalheadquarterposition__headquarter__commander__name__icontains=local_name)
            )

        if educational_name:
            queryset = queryset.filter(
                Q(usereducationalheadquarterposition__headquarter__name__icontains=educational_name) |
                Q(usereducationalheadquarterposition__headquarter__commander__name__icontains=educational_name)
            )

        if detachment_name:
            queryset = queryset.filter(
                Q(userdetachmentposition__headquarter__name__icontains=detachment_name) |
                Q(userdetachmentposition__headquarter__commander__name__icontains=detachment_name)
            )

        return queryset
