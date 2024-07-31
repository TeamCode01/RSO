import datetime as dt

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist

from api.serializers import (AreaSerializer, EducationalInstitutionSerializer,
                             RegionSerializer)
from competitions.models import CompetitionParticipants
from headquarters.models import (Area, CentralHeadquarter, Detachment,
                                 DistrictHeadquarter, EducationalHeadquarter,
                                 EducationalInstitution, LocalHeadquarter,
                                 Position, Region, RegionalHeadquarter,
                                 UserCentralHeadquarterPosition,
                                 UserDetachmentApplication,
                                 UserDetachmentPosition,
                                 UserDistrictHeadquarterPosition,
                                 UserEducationalHeadquarterPosition,
                                 UserLocalHeadquarterPosition,
                                 UserRegionalHeadquarterPosition,
                                 UserDistrictApplication,
                                 UserEducationalApplication,
                                 UserLocalApplication,
                                 UserRegionalApplication,
                                 UserCentralApplication,)
from users.models import RSOUser
from users.short_serializers import ShortUserSerializer, ShortestUserSerializer


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ('id', 'name',)


class BasePositionSerializer(serializers.ModelSerializer):
    """
    Базовый класс для вывода участников и их должностей
    при получении структурных единиц.
    """

    position = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(),
        required=False,
    )
    user = ShortUserSerializer(read_only=True)

    class Meta:
        model = UserCentralHeadquarterPosition
        fields = (
            'id',
            'user',
            'position',
            'is_trusted',
        )
        read_only_fields = ('user',)

    def to_representation(self, instance):
        serialized_data = super().to_representation(instance)
        position = instance.position
        if position:
            serialized_data['position'] = PositionSerializer(position).data
        return serialized_data


class CentralPositionSerializer(BasePositionSerializer):
    """Сериализатор для вывода участников при получении центрального штаба."""

    sub_commanders = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserCentralHeadquarterPosition
        fields = BasePositionSerializer.Meta.fields + ('sub_commanders',)
        read_only_fields = BasePositionSerializer.Meta.read_only_fields

    def get_sub_commanders(self, obj):
        commanders = []

        try:
            central_headquarter = obj.headquarter
            district_headquarters = DistrictHeadquarter.objects.filter(central_headquarter=central_headquarter)

            for district_hq in district_headquarters:
                if district_hq.commander:
                    commanders.append({
                        'id': district_hq.commander.id,
                        'type': 'DistrictHeadquarter',
                        'commander': district_hq.commander.get_full_name() if hasattr(district_hq.commander, 'get_full_name') else str(district_hq.commander),
                        'unit': district_hq.name
                    })

                regional_headquarters = RegionalHeadquarter.objects.filter(district_headquarter=district_hq)

                for regional_hq in regional_headquarters:
                    if regional_hq.commander:
                        commanders.append({
                            'id': regional_hq.commander.id,
                            'type': 'RegionalHeadquarter',
                            'commander': regional_hq.commander.get_full_name() if hasattr(regional_hq.commander, 'get_full_name') else str(regional_hq.commander),
                            'unit': regional_hq.name
                        })

                    detachments = Detachment.objects.filter(regional_headquarter=regional_hq)

                    for detachment in detachments:
                        if detachment.commander:
                            commanders.append({
                                'id': detachment.commander.id,
                                'type': 'Detachment',
                                'commander': detachment.commander.get_full_name() if hasattr(detachment.commander, 'get_full_name') else str(detachment.commander),
                                'unit': detachment.name
                            })

                    local_headquarters = LocalHeadquarter.objects.filter(regional_headquarter=regional_hq)

                    for local_hq in local_headquarters:
                        if local_hq.commander:
                            commanders.append({
                                'id': local_hq.commander.id,
                                'type': 'LocalHeadquarter',
                                'commander': local_hq.commander.get_full_name() if hasattr(local_hq.commander, 'get_full_name') else str(local_hq.commander),
                                'unit': local_hq.name
                            })

                    educational_headquarters = EducationalHeadquarter.objects.filter(regional_headquarter=regional_hq)

                    for edu_hq in educational_headquarters:
                        if edu_hq.commander:
                            commanders.append({
                                'id': edu_hq.commander.id,
                                'type': 'EducationalHeadquarter',
                                'commander': edu_hq.commander.get_full_name() if hasattr(edu_hq.commander, 'get_full_name') else str(edu_hq.commander),
                                'unit': edu_hq.name
                            })

        except CentralHeadquarter.DoesNotExist:
            raise serializers.ValidationError("Central headquarter does not exist for this position.")

        return commanders


class DistrictPositionSerializer(BasePositionSerializer):
    """Сериализатор для вывода участников при получении окружного штаба."""

    sub_commanders = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserDistrictHeadquarterPosition
        fields = BasePositionSerializer.Meta.fields + ('sub_commanders',)

    def get_sub_commanders(self, obj):
        commanders = []
        try:
            district_headquarter = obj.headquarter 
            regional_headquarters = RegionalHeadquarter.objects.filter(district_headquarter=district_headquarter)
        except ObjectDoesNotExist:
            raise serializers.ValidationError("Regional headquarters do not exist for this district headquarter.")

        for regional_hq in regional_headquarters:
            if regional_hq.commander:
                commander_name = regional_hq.commander.get_full_name() if hasattr(regional_hq.commander, 'get_full_name') else str(regional_hq.commander)
                commanders.append({
                    'id': regional_hq.commander.id,
                    'type': 'RegionalHeadquarter',
                    'commander': commander_name,
                    'unit': regional_hq.name
                })

            try:
                detachments = Detachment.objects.filter(regional_headquarter=regional_hq)
            except ObjectDoesNotExist:
                continue

            for detachment in detachments:
                if detachment.commander:
                    commander_name = detachment.commander.get_full_name() if hasattr(detachment.commander, 'get_full_name') else str(detachment.commander)
                    commanders.append({
                        'id': detachment.commander.id,
                        'type': 'Detachment',
                        'commander': commander_name,
                        'unit': detachment.name
                    })

            try:
                local_headquarters = LocalHeadquarter.objects.filter(regional_headquarter=regional_hq)
            except ObjectDoesNotExist:
                continue

            for local_hq in local_headquarters:
                if local_hq.commander:
                    commander_name = local_hq.commander.get_full_name() if hasattr(local_hq.commander, 'get_full_name') else str(local_hq.commander)
                    commanders.append({
                        'id': local_hq.commander.id,
                        'type': 'LocalHeadquarter',
                        'commander': commander_name,
                        'unit': local_hq.name
                    })

            try:
                educational_headquarters = EducationalHeadquarter.objects.filter(regional_headquarter=regional_hq)
            except ObjectDoesNotExist:
                continue

            for edu_hq in educational_headquarters:
                if edu_hq.commander:
                    commander_name = edu_hq.commander.get_full_name() if hasattr(edu_hq.commander, 'get_full_name') else str(edu_hq.commander)
                    commanders.append({
                        'id': edu_hq.commander.id,
                        'type': 'EducationalHeadquarter',
                        'commander': commander_name,
                        'unit': edu_hq.name
                    })

        return commanders


class RegionalPositionSerializer(BasePositionSerializer):
    """Сериализатор для вывода участников при получении регионального штаба."""

    sub_commanders = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserRegionalHeadquarterPosition
        fields = BasePositionSerializer.Meta.fields + ('sub_commanders',)

    def get_sub_commanders(self, obj):
        commanders = []

        try:
            regional_headquarter = obj.headquarter

            detachments = Detachment.objects.filter(regional_headquarter=regional_headquarter)
            for detachment in detachments:
                if detachment.commander:
                    commander_info = {
                        'id': detachment.commander.id,
                        'type': 'Detachment',
                        'commander': detachment.commander.get_full_name() if hasattr(detachment.commander, 'get_full_name') else str(detachment.commander),
                        'unit': detachment.name
                    }
                    commanders.append(commander_info)

            local_headquarters = LocalHeadquarter.objects.filter(regional_headquarter=regional_headquarter)
            for local_hq in local_headquarters:
                if local_hq.commander:
                    commander_info = {
                        'id': local_hq.commander.id,
                        'type': 'LocalHeadquarter',
                        'commander': local_hq.commander.get_full_name() if hasattr(local_hq.commander, 'get_full_name') else str(local_hq.commander),
                        'unit': local_hq.name
                    }
                    commanders.append(commander_info)

            educational_headquarters = EducationalHeadquarter.objects.filter(regional_headquarter=regional_headquarter)
            for edu_hq in educational_headquarters:
                if edu_hq.commander:
                    commander_info = {
                        'id': edu_hq.commander.id,
                        'type': 'EducationalHeadquarter',
                        'commander': edu_hq.commander.get_full_name() if hasattr(edu_hq.commander, 'get_full_name') else str(edu_hq.commander),
                        'unit': edu_hq.name
                    }
                    commanders.append(commander_info)

        except RegionalHeadquarter.DoesNotExist:
            raise serializers.ValidationError("Regional headquarter does not exist for this position.")

        return commanders


class LocalPositionSerializer(BasePositionSerializer):
    """Сериализатор для вывода участников при получении местного штаба."""

    sub_commanders = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserLocalHeadquarterPosition
        fields = BasePositionSerializer.Meta.fields + ('sub_commanders',)

    def get_sub_commanders(self, obj):
        commanders = []
        try:
            local_headquarter = obj.headquarter
            detachments = Detachment.objects.filter(local_headquarter=local_headquarter)
            for detachment in detachments:
                if detachment.commander:
                    commander_info = ({
                        'id': detachment.commander.id,
                        'type': 'Detachment',
                        'commander': detachment.commander.get_full_name() if hasattr(detachment.commander, 'get_full_name') else str(detachment.commander),
                        'unit': detachment.name
                    })
                    commanders.append(commander_info)

            educational_headquarters = EducationalHeadquarter.objects.filter(local_headquarter=local_headquarter)
            for edu_hq in educational_headquarters:
                if edu_hq.commander:
                    commander_info = {
                        'id': edu_hq.commander.id,
                        'type': 'EducationalHeadquarter',
                        'commander': edu_hq.commander.get_full_name() if hasattr(edu_hq.commander, 'get_full_name') else str(edu_hq.commander),
                        'unit': edu_hq.name
                    }
                    commanders.append(commander_info)

        except LocalHeadquarter.DoesNotExist:
            raise serializers.ValidationError("Local headquarter does not exist for this position.")

        return commanders


class EducationalPositionSerializer(BasePositionSerializer):
    """Сериализатор для вывода участников при получении образовательного штаба."""

    sub_commanders = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserEducationalHeadquarterPosition
        fields = BasePositionSerializer.Meta.fields + ('sub_commanders',)

    def get_sub_commanders(self, obj):
        commanders = []
        try:
            educational_headquarter = obj.headquarter
            detachments = Detachment.objects.filter(educational_headquarter=educational_headquarter)
        except ObjectDoesNotExist:
            raise serializers.ValidationError("Detachments do not exist for this educational headquarter.")

        for detachment in detachments:
            if detachment.commander:
                commander_info = {
                    'id': detachment.commander.id,
                    'type': 'Detachment',
                    'commander': detachment.commander.get_full_name() if hasattr(detachment.commander, 'get_full_name') else str(detachment.commander),
                    'unit': detachment.name
                }
                commanders.append(commander_info)

        return commanders

class DetachmentPositionSerializer(BasePositionSerializer):
    """Сериализаатор для добавления пользователя в отряд."""

    class Meta:
        model = UserDetachmentPosition
        fields = BasePositionSerializer.Meta.fields
        read_only_fields = BasePositionSerializer.Meta.read_only_fields


class BaseShortUnitSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для хранения общих полей штабов для короткого вывода.
    Хранит только поля id, name и banner.
    """

    class Meta:
        model = None
        fields = (
            'id',
            'name',
            'banner',
            'emblem'
        )


class ShortDistrictHeadquarterSerializer(BaseShortUnitSerializer):
    class Meta:
        model = DistrictHeadquarter
        fields = BaseShortUnitSerializer.Meta.fields


class ShortRegionalHeadquarterSerializer(BaseShortUnitSerializer):
    class Meta:
        model = RegionalHeadquarter
        fields = BaseShortUnitSerializer.Meta.fields


class ShortLocalHeadquarterSerializer(BaseShortUnitSerializer):
    class Meta:
        model = LocalHeadquarter
        fields = BaseShortUnitSerializer.Meta.fields


class ShortEducationalHeadquarterSerializer(BaseShortUnitSerializer):
    class Meta:
        model = EducationalHeadquarter
        fields = BaseShortUnitSerializer.Meta.fields


class ShortDetachmentSerializer(BaseShortUnitSerializer):
    class Meta:
        model = Detachment
        fields = BaseShortUnitSerializer.Meta.fields


class BaseShortUnitListSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для хранения общих полей штабов для короткого вывода
    при получении СПИСКА тех или иных структурных единиц.
    Хранит только поля id, name и banner.
    """

    members_count = serializers.SerializerMethodField(read_only=True)
    participants_count = serializers.SerializerMethodField(read_only=True)
    events_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = None
        fields = (
            'id',
            'name',
            'emblem',
            'founding_date',
            'members_count',
            'participants_count',
            'events_count',
        )

    @staticmethod
    def get_members_count(instance):
        if isinstance(instance, QuerySet):
            instance_type = type(instance.first())
        else:
            instance_type = type(instance)
        if issubclass(instance_type, CentralHeadquarter):
            return RSOUser.objects.filter(membership_fee=True).count()
        return instance.members.filter(user__membership_fee=True).count() + 1

    @staticmethod
    def get_participants_count(instance):
        if isinstance(instance, QuerySet):
            instance_type = type(instance.first())
        else:
            instance_type = type(instance)
        if issubclass(instance_type, CentralHeadquarter):
            return RSOUser.objects.count()
        return instance.members.count() + 1

    def get_events_count(self, instance):
        return instance.events.count()


class ShortDistrictHeadquarterListSerializer(BaseShortUnitListSerializer):
    class Meta:
        model = DistrictHeadquarter
        fields = BaseShortUnitListSerializer.Meta.fields


class ShortRegionalHeadquarterListSerializer(BaseShortUnitListSerializer):
    district_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=DistrictHeadquarter.objects.all(),
    )

    class Meta:
        model = RegionalHeadquarter
        fields = BaseShortUnitListSerializer.Meta.fields + (
            'district_headquarter',
        )

    def to_representation(self, instance):
        serialized_data = super().to_representation(instance)
        region = instance.region
        if region:
            serialized_data['region'] = RegionSerializer(region).data
        return serialized_data


class ShortLocalHeadquarterListSerializer(BaseShortUnitListSerializer):
    regional_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=RegionalHeadquarter.objects.all(),
    )

    class Meta:
        model = LocalHeadquarter
        fields = BaseShortUnitListSerializer.Meta.fields + (
            'regional_headquarter',
        )


class ShortEducationalHeadquarterListSerializer(BaseShortUnitListSerializer):
    educational_institution = serializers.PrimaryKeyRelatedField(
        queryset=EducationalInstitution.objects.all(),
    )
    regional_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=RegionalHeadquarter.objects.all(),
    )
    local_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=LocalHeadquarter.objects.all(),
        required=False,
    )

    class Meta:
        model = EducationalHeadquarter
        fields = BaseShortUnitListSerializer.Meta.fields + (
            'educational_institution',
            'local_headquarter',
            'regional_headquarter',
        )

    def to_representation(self, instance):
        serialized_data = super().to_representation(instance)
        educational_institution = instance.educational_institution
        serialized_data['educational_institution'] = (
            EducationalInstitutionSerializer(educational_institution).data
        )
        return serialized_data


class ShortDetachmentListSerializer(BaseShortUnitListSerializer):
    educational_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=EducationalHeadquarter.objects.all(),
        required=False,
    )
    local_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=LocalHeadquarter.objects.all(),
        required=False
    )
    regional_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=RegionalHeadquarter.objects.all(),
        required=False
    )
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all()
    )

    class Meta:
        model = Detachment
        fields = BaseShortUnitListSerializer.Meta.fields + (
            'educational_headquarter',
            'local_headquarter',
            'regional_headquarter',
            'region',
            'educational_institution',
            'area',
        )

    def to_representation(self, instance):
        serialized_data = super().to_representation(instance)
        educational_institution = instance.educational_institution
        area = instance.area
        region = instance.region
        serialized_data['educational_institution'] = (
            EducationalInstitutionSerializer(educational_institution).data
        )
        serialized_data['area'] = AreaSerializer(area).data
        serialized_data['region'] = RegionSerializer(region).data
        return serialized_data


class BaseUnitSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для хранения общей логики штабов.

    Предназначен для использования как родительский класс для всех
    сериализаторов штабов, обеспечивая наследование общих полей и методов.
    """

    _POSITIONS_MAPPING = {
        CentralHeadquarter: (
            UserCentralHeadquarterPosition, CentralPositionSerializer
        ),
        DistrictHeadquarter: (
            UserDistrictHeadquarterPosition, DistrictPositionSerializer
        ),
        RegionalHeadquarter: (
            UserRegionalHeadquarterPosition, RegionalPositionSerializer
        ),
        LocalHeadquarter: (
            UserLocalHeadquarterPosition, LocalPositionSerializer
        ),
        EducationalHeadquarter: (
            UserEducationalHeadquarterPosition, EducationalPositionSerializer
        ),
        Detachment: (UserDetachmentPosition, DetachmentPositionSerializer),
    }

    commander = serializers.PrimaryKeyRelatedField(
        queryset=RSOUser.objects.all(),
    )
    members_count = serializers.SerializerMethodField(read_only=True)
    participants_count = serializers.SerializerMethodField(read_only=True)
    leadership = serializers.SerializerMethodField(read_only=True)
    events_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = None
        fields = (
            'id',
            'name',
            'commander',
            'about',
            'emblem',
            'social_vk',
            'social_tg',
            'banner',
            'slogan',
            'city',
            'members_count',
            'participants_count',
            'events_count',
            'leadership',
        )

    def to_representation(self, instance):
        """Переопределяем представление данных для полей commader."""
        serialized_data = super().to_representation(instance)
        commander = instance.commander
        if commander:
            serialized_data['commander'] = ShortUserSerializer(commander).data
        return serialized_data

    def _get_position_instance(self):
        if isinstance(self.instance, QuerySet):
            instance_type = type(self.instance.first())
        else:
            instance_type = type(self.instance)

        for model_class, (
                position_model, _
        ) in self._POSITIONS_MAPPING.items():
            if issubclass(instance_type, model_class):
                return position_model

    def _get_position_serializer(self):
        if isinstance(self.instance, QuerySet):
            instance_type = type(self.instance.first())
        else:
            instance_type = type(self.instance)

        for model_class, (
                _, serializer_class
        ) in self._POSITIONS_MAPPING.items():
            if issubclass(instance_type, model_class):
                return serializer_class

    def get_leadership(self, instance):
        """
        Вывод руководство отряда - всех, кроме указанных в настройках
        должностей.
        """
        serializer = self._get_position_serializer()
        position_instance = self._get_position_instance()
        leaders = position_instance.objects.filter(
            headquarter=instance
        ).exclude(
            Q(position__name__in=settings.NOT_LEADERSHIP_POSITIONS) |
            Q(position__isnull=True)
        )

        return serializer(leaders, many=True).data

    def get_events_count(self, instance):
        return instance.events.count()

    @staticmethod
    def get_members_count(instance):
        if isinstance(instance, QuerySet):
            instance_type = type(instance.first())
        else:
            instance_type = type(instance)
        if issubclass(instance_type, CentralHeadquarter):
            return RSOUser.objects.filter(membership_fee=True).count()
        return instance.members.filter(user__membership_fee=True).count() + 1

    @staticmethod
    def get_participants_count(instance):
        if isinstance(instance, QuerySet):
            instance_type = type(instance.first())
        else:
            instance_type = type(instance)
        if issubclass(instance_type, CentralHeadquarter):
            return RSOUser.objects.count()
        return instance.members.count() + 1

    def update(self, instance, validated_data):
        try:
            super().update(instance, validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        return instance

    def create(self, validated_data):
        try:
            super().create(validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    def validate(self, attrs):
        """
        Запрещает назначить пользователя командиром, если он уже им является.
        """
        commander_id = attrs.get('commander')
        print('валидириуем')
        print('командир айди:', commander_id)
        print(self.instance)
        if commander_id:
            instance_type = self.Meta.model
            print(f'INSTANCE TYPE: {instance_type}')
            for model_class in self._POSITIONS_MAPPING:
                if not issubclass(instance_type, model_class):
                    continue
                print(f'MODEL CLASS: {model_class}')
                existing_units = model_class.objects.exclude(
                    id=getattr(self.instance, 'id', None))

                if existing_units.filter(commander=commander_id).exists():
                    raise serializers.ValidationError(
                        f"Пользователь уже является командиром другого "
                        f"{model_class.__name__}."
                    )

        return attrs


class CentralHeadquarterSerializer(BaseUnitSerializer):
    """Сериализатор для центрального штаба.

    Наследует общую логику и поля от BaseUnitSerializer и связывает
    с моделью CentralHeadquarter.
    """
    working_years = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CentralHeadquarter
        fields = BaseUnitSerializer.Meta.fields + (
            'working_years',
            'detachments_appearance_year',
            'rso_founding_congress_date',
        )

    @staticmethod
    def get_working_years(instance):
        return (
            dt.datetime.now().year - settings.CENTRAL_HEADQUARTER_FOUNDING_DATE
        )  

class DistrictHeadquarterSerializer(BaseUnitSerializer):
    """Сериализатор для окружного штаба.

    Дополнительно к полям из BaseUnitSerializer, добавляет поле
    central_headquarter для связи с центральным штабом.
    """

    central_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=CentralHeadquarter.objects.all(),
        required=False
    )
    commander = serializers.PrimaryKeyRelatedField(
        queryset=RSOUser.objects.all(),
    )
    regional_headquarters = serializers.SerializerMethodField()
    local_headquarters = serializers.SerializerMethodField()
    educational_headquarters = serializers.SerializerMethodField()
    detachments = serializers.SerializerMethodField()

    class Meta:
        model = DistrictHeadquarter
        fields = BaseUnitSerializer.Meta.fields + (
            'central_headquarter',
            'founding_date',
            'members',
            'regional_headquarters',
            'local_headquarters',
            'educational_headquarters',
            'detachments',
        )
        read_only_fields = ('regional_headquarters',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_units = None

    def _get_units(self, obj):
        """
        Сохраняем юниты в кэш и отдаем их. Если есть в кэше, берем оттуда.
        """
        if self._cached_units is None:
            self._cached_units = obj.get_related_units()
        return self._cached_units

    def get_regional_headquarters(self, obj):
        units = self._get_units(obj)
        regional_headquarters_serializer = (
            ShortEducationalHeadquarterSerializer(
                units['regional_headquarters'], many=True
            )
        ).data
        return regional_headquarters_serializer

    def get_educational_headquarters(self, obj):
        units = self._get_units(obj)
        educational_headquarters_serializer = (
            ShortEducationalHeadquarterSerializer(
                units['educational_headquarters'], many=True
            )
        ).data
        return educational_headquarters_serializer

    def get_local_headquarters(self, obj):
        units = self._get_units(obj)
        local_headquarters_serializer = ShortLocalHeadquarterSerializer(
            units['local_headquarters'], many=True
        ).data
        return local_headquarters_serializer

    def get_detachments(self, obj):
        units = self._get_units(obj)
        detachment_serializer = ShortDetachmentSerializer(
            units['detachments'], many=True
        ).data
        return detachment_serializer

    def to_representation(self, obj):
        """Для очищения кэша перед началом сериализации."""
        self._cached_units = None
        return super().to_representation(obj)
    

class RegionalHeadquarterSerializer(BaseUnitSerializer):
    """Сериализатор для регионального штаба.

    Включает в себя поля из BaseUnitSerializer, а также поля region и
    district_headquarter для указания региона и привязки к окружному штабу.
    Выводит пользователей для верификации.
    """

    region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all()
    )
    district_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=DistrictHeadquarter.objects.all(),
    )
    detachments = serializers.SerializerMethodField(read_only=True)
    local_headquarters = serializers.SerializerMethodField(read_only=True)
    educational_headquarters = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = RegionalHeadquarter
        fields = BaseUnitSerializer.Meta.fields + (
            'region',
            'district_headquarter',
            'name_for_certificates',
            'conference_date',
            'registry_date',
            'registry_number',
            'case_name',
            'legal_address',
            'requisites',
            'founding_date',
            'detachments',
            'local_headquarters',
            'educational_headquarters',
        )
        read_only_fields = (
            'detachments',
            'local_headquarters',
            'educational_headquarters',
        )

    def to_representation(self, instance):
        """
        Вызывает родительский метод to_representation,
        а также изменяем вывод region + очищаем кэш.
        """
        serialized_data = super().to_representation(instance)
        region = instance.region
        if region:
            serialized_data['region'] = RegionSerializer(region).data
        self._cached_units = None
        return serialized_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_units = None

    def _get_units(self, obj):
        """
        Сохраняем юниты в кэш и отдаем их. Если есть в кэше, берем оттуда.
        """
        if self._cached_units is None:
            self._cached_units = obj.get_related_units()
        return self._cached_units

    def get_educational_headquarters(self, obj):
        units = self._get_units(obj)
        educational_headquarters_serializer = (
            ShortEducationalHeadquarterSerializer(
                units['educational_headquarters'], many=True
            )
        ).data
        return educational_headquarters_serializer

    def get_local_headquarters(self, obj):
        units = self._get_units(obj)
        local_headquarters_serializer = ShortLocalHeadquarterSerializer(
            units['local_headquarters'], many=True
        ).data
        return local_headquarters_serializer

    def get_detachments(self, obj):
        units = self._get_units(obj)
        detachment_serializer = ShortDetachmentSerializer(
            units['detachments'], many=True
        ).data
        return detachment_serializer


class LocalHeadquarterSerializer(BaseUnitSerializer):
    """Сериализатор для местного штаба.

    Расширяет BaseUnitSerializer, добавляя поле regional_headquarter
    для связи с региональным штабом.
    """

    regional_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=RegionalHeadquarter.objects.all(),
    )
    educational_headquarters = serializers.SerializerMethodField(
        read_only=True
    )
    detachments = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = LocalHeadquarter
        fields = BaseUnitSerializer.Meta.fields + (
            'regional_headquarter',
            'founding_date',
            'educational_headquarters',
            'detachments',
        )
        read_only_fields = ('educational_headquarters', 'detachments',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_units = None

    def create(self, validated_data):
        """
        Создает и возвращает новый экземпляр LocalHeadquarter.
        """
        try:
            return LocalHeadquarter.objects.create(**validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    def to_representation(self, instance):
        """Очищаем кэш."""
        self._cached_units = None
        return super().to_representation(instance)

    def _get_units(self, obj):
        """
        Сохраняем юниты в кэш и отдаем их. Если есть в кэше, берем оттуда.
        """
        if self._cached_units is None:
            self._cached_units = obj.get_related_units()
        return self._cached_units

    def get_educational_headquarters(self, obj):
        units = self._get_units(obj)
        educational_headquarters_serializer = (
            ShortEducationalHeadquarterSerializer(
                units['educational_headquarters'], many=True
            )
        ).data
        return educational_headquarters_serializer

    def get_detachments(self, obj):
        units = self._get_units(obj)
        detachment_serializer = ShortDetachmentSerializer(
            units['detachments'], many=True
        ).data
        return detachment_serializer


class EducationalHeadquarterSerializer(BaseUnitSerializer):
    """Сериализатор для образовательного штаба.

    Содержит ссылки на образовательное учреждение и связанные
    местный и региональный штабы. Включает в себя валидацию для
    проверки согласованности связей между штабами.
    """

    educational_institution = serializers.PrimaryKeyRelatedField(
        queryset=EducationalInstitution.objects.all(),
    )
    regional_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=RegionalHeadquarter.objects.all(),
    )
    local_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=LocalHeadquarter.objects.all(),
        required=False,
        allow_null=True
    )
    detachments = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = EducationalHeadquarter
        fields = BaseUnitSerializer.Meta.fields + (
            'educational_institution',
            'local_headquarter',
            'regional_headquarter',
            'founding_date',
            'detachments',
        )
        read_only_fields = ('detachments',)

    def create(self, validated_data):
        """
        Создает и возвращает новый экземпляр EducationalHeadquarter.
        """
        try:
            return EducationalHeadquarter.objects.create(**validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    def to_representation(self, instance):
        """
        Вызывает родительский метод to_representation,
        а также изменяет вывод educational_institution.
        Очищаем кэш.
        """
        serialized_data = super().to_representation(instance)
        educational_institution = instance.educational_institution
        serialized_data['educational_institution'] = (
            EducationalInstitutionSerializer(educational_institution).data
        )
        return serialized_data

    @staticmethod
    def _get_units(obj):
        """Получаем связанные объекты (отряды)."""
        return obj.get_related_units()

    def get_detachments(self, obj):
        return (
            ShortDetachmentSerializer(
                self._get_units(obj)['detachments'], many=True
            ).data
        )


class BaseApplicationSerializer(serializers.ModelSerializer):
    """Базовый класс для сериализаторов заявок."""

    class Meta:
        model = None
        fields = ('id', 'user',)
        read_only_fields = ('user',)

    def validate(self, attrs):
        user = self.context['request'].user
        if self.Meta.model.objects.filter(user=user).exists():
            raise ValidationError('Вы уже подали заявку.')

        headquarter_or_detachment = self.get_headquarter_or_detachment()
        try:
            hq_region = headquarter_or_detachment.regional_headquarter.region
            if hq_region != user.region:
                raise ValidationError(
                    'Нельзя подать заявку вне своего региона.'
                )
        except AttributeError:
            pass
        return attrs

    def get_headquarter_or_detachment(self):
        raise NotImplementedError


class UserDetachmentApplicationSerializer(BaseApplicationSerializer):
    """Сериализатор для подачи заявок в отряд."""

    class Meta(BaseApplicationSerializer.Meta):
        model = UserDetachmentApplication

    def get_headquarter_or_detachment(self):
        try:
            return Detachment.objects.get(
                id=self.context['view'].kwargs.get('pk')
            )
        except Detachment.DoesNotExist:
            raise ValidationError('Отряд не найден.')


class UserEducationalApplicationSerializer(BaseApplicationSerializer):
    """Сериализатор для подачи заявок в обр. штаб."""

    class Meta(BaseApplicationSerializer.Meta):
        model = UserEducationalApplication

    def get_headquarter_or_detachment(self):
        try:
            return EducationalHeadquarter.objects.get(
                id=self.context['view'].kwargs.get('pk')
            )
        except EducationalHeadquarter.DoesNotExist:
            raise ValidationError('Образовательный штаб не найден.')


class UserLocalApplicationSerializer(BaseApplicationSerializer):
    """Сериализатор для подачи заявок в местный штаб."""

    class Meta(BaseApplicationSerializer.Meta):
        model = UserLocalApplication

    def get_headquarter_or_detachment(self):
        try:
            return LocalHeadquarter.objects.get(
                id=self.context['view'].kwargs.get('pk')
            )
        except LocalHeadquarter.DoesNotExist:
            raise ValidationError('Местный штаб не найден.')


class UserRegionalApplicationSerializer(BaseApplicationSerializer):
    """Сериализатор для подачи заявок в региональный штаб."""

    class Meta(BaseApplicationSerializer.Meta):
        model = UserRegionalApplication

    def get_headquarter_or_detachment(self):
        try:
            return RegionalHeadquarter.objects.get(
                id=self.context['view'].kwargs.get('pk')
            )
        except RegionalHeadquarter.DoesNotExist:
            raise ValidationError('Региональный штаб не найден.')


class UserDistrictApplicationSerializer(BaseApplicationSerializer):
    """Сериализатор для подачи заявок в окружной штаб."""

    class Meta(BaseApplicationSerializer.Meta):
        model = UserDistrictApplication

    def get_headquarter_or_detachment(self):
        try:
            return DistrictHeadquarter.objects.get(
                id=self.context['view'].kwargs.get('pk')
            )
        except DistrictHeadquarter.DoesNotExist:
            raise ValidationError('Окружной штаб не найден.')


class UserCentralApplicationSerializer(BaseApplicationSerializer):
    """Сериализатор для подачи заявок в центральный штаб."""

    class Meta(BaseApplicationSerializer.Meta):
        model = UserCentralApplication

    def get_headquarter_or_detachment(self):
        try:
            return CentralHeadquarter.objects.get(
                id=self.context['view'].kwargs.get('pk')
            )
        except CentralHeadquarter.DoesNotExist:
            raise ValidationError('Центральный штаб не найден.')


class BaseApplicationReadSerializer(serializers.ModelSerializer):
    """Базовый класс для чтения заявок."""

    user = ShortUserSerializer(read_only=True)

    class Meta:
        model = None
        fields = ('id', 'user')
        read_only_fields = ('user',)


class UserDetachmentApplicationReadSerializer(BaseApplicationReadSerializer):
    """Сериализатор для чтения заявок в отряд."""

    class Meta(BaseApplicationReadSerializer.Meta):
        model = UserDetachmentApplication


class UserEducationalApplicationReadSerializer(BaseApplicationReadSerializer):
    """Сериализатор для чтения заявок в образовательный штаб."""

    class Meta(BaseApplicationReadSerializer.Meta):
        model = UserEducationalApplication


class UserLocalApplicationReadSerializer(BaseApplicationReadSerializer):
    """Сериализатор для чтения заявок в местный штаб."""

    class Meta(BaseApplicationReadSerializer.Meta):
        model = UserLocalApplication


class UserRegionalApplicationReadSerializer(BaseApplicationReadSerializer):
    """Сериализатор для чтения заявок в региональный штаб."""

    class Meta(BaseApplicationReadSerializer.Meta):
        model = UserRegionalApplication


class UserDistrictApplicationReadSerializer(BaseApplicationReadSerializer):
    """Сериализатор для чтения заявок в окружной штаб."""

    class Meta(BaseApplicationReadSerializer.Meta):
        model = UserDistrictApplication


class UserCentralApplicationReadSerializer(BaseApplicationReadSerializer):
    """Сериализатор для чтения заявок в центральный штаб."""

    class Meta(BaseApplicationReadSerializer.Meta):
        model = UserCentralApplication


class BaseApplicationShortReadSerializer(serializers.ModelSerializer):
    """Базовый класс для чтения заявок."""

    user = ShortestUserSerializer(read_only=True)

    class Meta:
        model = None
        fields = ('id', 'user')
        read_only_fields = ('user',)


class UserDetachmentApplicationShortReadSerializer(
    BaseApplicationShortReadSerializer
):
    """Сериализатор для чтения заявок в отряд."""

    class Meta(BaseApplicationShortReadSerializer.Meta):
        model = UserDetachmentApplication


class UserEducationalApplicationShortReadSerializer(
    BaseApplicationShortReadSerializer
):
    """Сериализатор для чтения заявок в образовательный штаб."""

    class Meta(BaseApplicationShortReadSerializer.Meta):
        model = UserEducationalApplication


class UserLocalApplicationShortReadSerializer(
    BaseApplicationShortReadSerializer
):
    """Сериализатор для чтения заявок в местный штаб."""

    class Meta(BaseApplicationShortReadSerializer.Meta):
        model = UserLocalApplication


class UserRegionalApplicationShortReadSerializer(
    BaseApplicationShortReadSerializer
):
    """Сериализатор для чтения заявок в региональный штаб."""

    class Meta(BaseApplicationShortReadSerializer.Meta):
        model = UserRegionalApplication


class UserDistrictApplicationShortReadSerializer(
    BaseApplicationShortReadSerializer
):
    """Сериализатор для чтения заявок в окружной штаб."""

    class Meta(BaseApplicationShortReadSerializer.Meta):
        model = UserDistrictApplication


class UserCentralApplicationShortReadSerializer(
    BaseApplicationShortReadSerializer
):
    """Сериализатор для чтения заявок в центральный штаб."""

    class Meta(BaseApplicationShortReadSerializer.Meta):
        model = UserCentralApplication


class DetachmentSerializer(BaseUnitSerializer):
    """Сериализатор для отряда.

    Наследует общие поля из BaseUnitSerializer и добавляет специфические поля
    для отряда, включая связи с образовательным, местным и региональным
    штабами, а также поле для указания области деятельности (area).
    Включает в себя валидацию для
    проверки согласованности связей между штабами.
    """

    educational_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=EducationalHeadquarter.objects.all(),
        required=False,
        allow_null=True
    )
    local_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=LocalHeadquarter.objects.all(),
        required=False,
        allow_null=True
    )
    regional_headquarter = serializers.PrimaryKeyRelatedField(
        queryset=RegionalHeadquarter.objects.all(),
        required=False
    )
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all()
    )
    nomination = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    tandem_partner = serializers.SerializerMethodField()

    class Meta:
        model = Detachment
        fields = BaseUnitSerializer.Meta.fields + (
            'educational_headquarter',
            'local_headquarter',
            'regional_headquarter',
            'region',
            'educational_institution',
            'city',
            'area',
            'photo1',
            'photo2',
            'photo3',
            'photo4',
            'city',
            'founding_date',
            'nomination',
            'status',
            'tandem_partner',
        )

    def create(self, validated_data):
        """
        Создает и возвращает новый экземпляр Detachment.
        """
        try:
            return Detachment.objects.create(**validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    def to_representation(self, instance):
        """
        Вызывает родительский метод to_representation,
        а также изменяет вывод educational_institution.
        """
        serialized_data = super().to_representation(instance)
        educational_institution = instance.educational_institution
        area = instance.area
        region = instance.region
        serialized_data['educational_institution'] = (
            EducationalInstitutionSerializer(educational_institution).data
        )
        serialized_data['area'] = AreaSerializer(area).data
        serialized_data['region'] = RegionSerializer(region).data
        return serialized_data

    def get_leadership(self, instance):
        """
        Вывод руководства отряда (пользователи с должностями "Мастер
        (методист)" и "Комиссар", точные названия которых прописаны
        в настройках).
        """
        serializer = self._get_position_serializer()
        position_instance = self._get_position_instance()
        leaders = position_instance.objects.filter(
            Q(headquarter=instance) &
            Q(position__name=settings.MASTER_METHODIST_POSITION_NAME) |
            Q(position__name=settings.COMMISSIONER_POSITION_NAME)
        )
        return serializer(leaders, many=True).data

    def get_status(self, obj):
        if not CompetitionParticipants.objects.filter(
            Q(detachment=obj) & Q(junior_detachment__isnull=False) |
            Q(detachment__isnull=False) & Q(junior_detachment=obj)
        ).exists():
            return None
        if CompetitionParticipants.objects.filter(
            Q(detachment=obj) & Q(junior_detachment__isnull=False)
        ).exists():
            return 'Наставник'
        return 'Старт'

    def get_nomination(self, obj):
        if not CompetitionParticipants.objects.filter(
            Q(detachment=obj) & Q(junior_detachment__isnull=False) |
            Q(detachment__isnull=False) & Q(junior_detachment=obj) |
            Q(junior_detachment=obj)
        ).exists():
            return None
        if CompetitionParticipants.objects.filter(
            Q(detachment=obj) & Q(junior_detachment__isnull=False) |
            Q(detachment__isnull=False) & Q(junior_detachment=obj)
        ).exists():
            return 'Тандем'
        return 'Дебют'

    def get_tandem_partner(self, obj):
        participants = CompetitionParticipants.objects.filter(
            Q(detachment=obj) | Q(junior_detachment=obj)
        ).first()
        if participants:
            if participants.detachment == obj:
                return ShortDetachmentSerializer(
                    participants.junior_detachment
                ).data
            if participants.detachment:
                return ShortDetachmentSerializer(
                    participants.detachment
                ).data


class DetachmentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detachment
        fields = ('id', 'name', 'local_headquarter', 'educational_headquarter', 'regional_headquarter')