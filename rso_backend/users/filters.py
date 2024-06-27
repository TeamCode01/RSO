from django_filters import rest_framework as filters
from users.models import RSOUser
from headquarters.models import Detachment, DistrictHeadquarter, RegionalHeadquarter, LocalHeadquarter, EducationalHeadquarter, CentralHeadquarter

class RSOUserFilter(filters.FilterSet):
    date_of_birth = filters.DateFilter()
    date_of_birth_gte = filters.DateFilter(
        field_name='date_of_birth', lookup_expr='gte'
    )
    date_of_birth_lte = filters.DateFilter(
        field_name='date_of_birth', lookup_expr='lte'
    )
    central_headquarter__name = filters.CharFilter(
        method='filter_central_headquarter',
        label='Название центрального штаба'
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
            'central_headquarter__name',
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

    def filter_central_headquarter(self, queryset, name, value):
        headquarters = CentralHeadquarter.objects.filter(name__iexact=value)
        user_ids = set()
        for headquarter in headquarters:
            if headquarter.commander:
                user_ids.add(headquarter.commander.id)
            user_ids.update(headquarter.members.values_list('user_id', flat=True))

            district_headquarters = headquarter.district_headquarters.all()
            for district_hq in district_headquarters:
                if district_hq.commander:
                    user_ids.add(district_hq.commander.id)
                user_ids.update(district_hq.members.values_list('user_id', flat=True))

                regional_headquarters = district_hq.regional_headquarters.all()
                for regional_hq in regional_headquarters:
                    if regional_hq.commander:
                        user_ids.add(regional_hq.commander.id)
                    user_ids.update(regional_hq.members.values_list('user_id', flat=True))

                    detachments = regional_hq.detachments.all()
                    for detachment in detachments:
                        if detachment.commander:
                            user_ids.add(detachment.commander.id)
                        user_ids.update(detachment.members.values_list('user_id', flat=True))

                    local_headquarters = regional_hq.local_headquarters.all()
                    for local_hq in local_headquarters:
                        if local_hq.commander:
                            user_ids.add(local_hq.commander.id)
                        user_ids.update(local_hq.members.values_list('user_id', flat=True))

                    educational_headquarters = regional_hq.educational_headquarters.all()
                    for edu_hq in educational_headquarters:
                        if edu_hq.commander:
                            user_ids.add(edu_hq.commander.id)
                        user_ids.update(edu_hq.members.values_list('user_id', flat=True))
        return queryset.filter(id__in=user_ids)

    def filter_district_headquarter(self, queryset, name, value):
        headquarters = DistrictHeadquarter.objects.filter(name__iexact=value)
        user_ids = set()
        for headquarter in headquarters:
            if headquarter.commander:
                user_ids.add(headquarter.commander.id)
            user_ids.update(headquarter.members.values_list('user_id', flat=True))
            
            regional_headquarters = headquarter.regional_headquarters.all()
            for regional_hq in regional_headquarters:
                if regional_hq.commander:
                    user_ids.add(regional_hq.commander.id)
                user_ids.update(regional_hq.members.values_list('user_id', flat=True))

                detachments = regional_hq.detachments.all()
                for detachment in detachments:
                    if detachment.commander:
                        user_ids.add(detachment.commander.id)
                    user_ids.update(detachment.members.values_list('user_id', flat=True))

                local_headquarters = regional_hq.local_headquarters.all()
                for local_hq in local_headquarters:
                    if local_hq.commander:
                        user_ids.add(local_hq.commander.id)
                    user_ids.update(local_hq.members.values_list('user_id', flat=True))

                educational_headquarters = regional_hq.educational_headquarters.all()
                for edu_hq in educational_headquarters:
                    if edu_hq.commander:
                        user_ids.add(edu_hq.commander.id)
                    user_ids.update(edu_hq.members.values_list('user_id', flat=True))
        return queryset.filter(id__in=user_ids)

    def filter_regional_headquarter(self, queryset, name, value):
        headquarters = RegionalHeadquarter.objects.filter(name__iexact=value)
        user_ids = set()
        for headquarter in headquarters:
            if headquarter.commander:
                user_ids.add(headquarter.commander.id)
            user_ids.update(headquarter.members.values_list('user_id', flat=True))

            detachments = headquarter.detachments.all()
            for detachment in detachments:
                if detachment.commander:
                    user_ids.add(detachment.commander.id)
                user_ids.update(detachment.members.values_list('user_id', flat=True))

            local_headquarters = headquarter.local_headquarters.all()
            for local_hq in local_headquarters:
                if local_hq.commander:
                    user_ids.add(local_hq.commander.id)
                user_ids.update(local_hq.members.values_list('user_id', flat=True))

            educational_headquarters = headquarter.educational_headquarters.all()
            for edu_hq in educational_headquarters:
                if edu_hq.commander:
                    user_ids.add(edu_hq.commander.id)
                user_ids.update(edu_hq.members.values_list('user_id', flat=True))
                
        return queryset.filter(id__in=user_ids)

    def filter_local_headquarter(self, queryset, name, value):
        headquarters = LocalHeadquarter.objects.filter(name__iexact=value)
        user_ids = set()
        for headquarter in headquarters:
            if headquarter.commander:
                user_ids.add(headquarter.commander.id)
            user_ids.update(headquarter.members.values_list('user_id', flat=True))

            detachments = headquarter.detachments.all()
            for detachment in detachments:
                if detachment.commander:
                    user_ids.add(detachment.commander.id)
                user_ids.update(detachment.members.values_list('user_id', flat=True))
                
        return queryset.filter(id__in=user_ids)

    def filter_educational_headquarter(self, queryset, name, value):
        headquarters = EducationalHeadquarter.objects.filter(name__iexact=value)
        user_ids = set()
        for headquarter in headquarters:
            if headquarter.commander:
                user_ids.add(headquarter.commander.id)
            user_ids.update(headquarter.members.values_list('user_id', flat=True))

            detachments = headquarter.detachments.all()
            for detachment in detachments:
                if detachment.commander:
                    user_ids.add(detachment.commander.id)
                user_ids.update(detachment.members.values_list('user_id', flat=True))
                
        return queryset.filter(id__in=user_ids)

    def filter_detachment_headquarter(self, queryset, name, value):
        headquarters = Detachment.objects.filter(name__iexact=value)
        user_ids = set()
        for headquarter in headquarters:
            if headquarter.commander:
                user_ids.add(headquarter.commander.id)
            user_ids.update(headquarter.members.values_list('user_id', flat=True))
                
        return queryset.filter(id__in=user_ids)
