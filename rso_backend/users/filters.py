from django_filters import rest_framework as filters
from users.models import RSOUser
from headquarters.models import Detachment, DistrictHeadquarter, RegionalHeadquarter, LocalHeadquarter, EducationalHeadquarter

class RSOUserFilter(filters.FilterSet):
    date_of_birth = filters.DateFilter()
    date_of_birth_gte = filters.DateFilter(
        field_name='date_of_birth', lookup_expr='gte'
    )
    date_of_birth_lte = filters.DateFilter(
        field_name='date_of_birth', lookup_expr='lte'
    )
    district_headquarter__name = filters.CharFilter(
        method='filter_district_headquarter',
        label='Название окружного штаба'
    )
    regional_headquarter__name = filters.CharFilter(
        method='filter_regional_headquarter',
        label='Название регионального штаба'
    )
    local_headquarter__name = filters.CharFilter(
        method='filter_local_headquarter',
        label='Название местного штаба'
    )
    educational_headquarter__name = filters.CharFilter(
        method='filter_educational_headquarter',
        label='Название образовательного штаба'
    )
    detachment__name = filters.CharFilter(
        method='filter_detachment_headquarter',
        label='Название отряда'
    )
    region = filters.CharFilter(
        field_name='region__name',
        lookup_expr='iexact',
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

    def filter_district_headquarter(self, queryset, name, value):
        headquarters = DistrictHeadquarter.objects.filter(name__iexact=value)
        user_ids = []
        for headquarter in headquarters:
            user_ids.append(headquarter.commander.id)
            user_ids.extend(headquarter.members.values_list('user_id', flat=True))
        return queryset.filter(id__in=user_ids)

    def filter_regional_headquarter(self, queryset, name, value):
        headquarters = RegionalHeadquarter.objects.filter(name__iexact=value)
        user_ids = []
        for headquarter in headquarters:
            user_ids.append(headquarter.commander.id)
            user_ids.extend(headquarter.members.values_list('user_id', flat=True))
        return queryset.filter(id__in=user_ids)

    def filter_local_headquarter(self, queryset, name, value):
        headquarters = LocalHeadquarter.objects.filter(name__iexact=value)
        user_ids = []
        for headquarter in headquarters:
            user_ids.append(headquarter.commander.id)
            user_ids.extend(headquarter.members.values_list('user_id', flat=True))
        return queryset.filter(id__in=user_ids)

    def filter_educational_headquarter(self, queryset, name, value):
        headquarters = EducationalHeadquarter.objects.filter(name__iexact=value)
        user_ids = []
        for headquarter in headquarters:
            user_ids.append(headquarter.commander.id)
            user_ids.extend(headquarter.members.values_list('user_id', flat=True))
        return queryset.filter(id__in=user_ids)

    def filter_detachment_headquarter(self, queryset, name, value):
        headquarters = Detachment.objects.filter(name__iexact=value)
        user_ids = []
        for headquarter in headquarters:
            user_ids.append(headquarter.commander.id)
            user_ids.extend(headquarter.members.values_list('user_id', flat=True))
        return queryset.filter(id__in=user_ids)
