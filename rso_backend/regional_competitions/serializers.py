from django.db import models
from rest_framework import serializers

from api.utils import create_first_or_exception
from regional_competitions.constants import (CONVERT_TO_MB, REPORT_EXISTS_MESSAGE,
                                             REPORT_SENT_MESSAGE, ROUND_2_SIGNS,
                                             STATISTICAL_REPORT_EXISTS_MESSAGE)
from regional_competitions.factories import RSerializerFactory
from regional_competitions.models import (CHqRejectingLog, RegionalR1, RegionalR18, RegionalR18Link, RegionalR18Project,
                                          RegionalR4, RegionalR4Event,
                                          RegionalR4Link, RegionalR5,
                                          RegionalR5Event, RegionalR5Link,
                                          RegionalR11, RegionalR12,
                                          RegionalR13, RegionalR16,
                                          RegionalR16Link, RegionalR16Project,
                                          RegionalR17, RegionalR19,
                                          RegionalR101, RegionalR101Link,
                                          RegionalR102, RegionalR102Link,
                                          RVerificationLog,
                                          StatisticalRegionalReport,
                                          r6_models_factory,
                                          r7_models_factory, r9_models_factory)
from regional_competitions.utils import get_report_number_by_class_name


class StatisticalRegionalReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatisticalRegionalReport
        fields = (
            'id',
            'participants_number',
            'regional_headquarter',
            'employed_sso',
            'employed_spo',
            'employed_sop',
            'employed_smo',
            'employed_sservo',
            'employed_ssho',
            'employed_specialized_detachments',
            'employed_production_detachments',
            'employed_top',
        )
        read_only_fields = ('id', 'regional_headquarter')
        extra_kwargs = {
            'id': {'read_only': True},
            'regional_headquarter': {
                'help_text': 'ID регионального штаба для которого создается или запрашивается отчет.'
            },
        }

    def create(self, validated_data):
        return create_first_or_exception(
            self,
            validated_data,
            StatisticalRegionalReport,
            STATISTICAL_REPORT_EXISTS_MESSAGE
        )


class FileScanSizeSerializerMixin(serializers.ModelSerializer):
    """Миксин для добавления свойств размера и типа файла в сериализатор."""
    file_size = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()

    class Meta:
        fields = ('file_size', 'file_type')
        model = None

    def get_file_field(self):
        """Автоматически находит поле типа FileField в модели."""
        if not hasattr(self, '_file_field_name'):
            for field in self.Meta.model._meta.fields:
                if isinstance(field, models.FileField):
                    self._file_field_name = field.name
                    break
            else:
                self._file_field_name = None
        return self._file_field_name

    def get_file_size(self, obj):
        file_field_name = self.get_file_field()
        if not file_field_name:
            return None
        check_file = getattr(obj, file_field_name)
        if check_file:
            return round(check_file.size / CONVERT_TO_MB, ROUND_2_SIGNS)
        return None

    def get_file_type(self, obj):
        file_field_name = self.get_file_field()
        if not file_field_name:
            return None
        check_file = getattr(obj, file_field_name)
        if check_file:
            return check_file.name.split('.')[-1]
        return None


class NestedCreateUpdateMixin:
    """
    Миксин для сериализаторов, которые реализуют логику
    создания и обновления для двух уровней вложенных объектов.
    """

    nested_objects_name = None

    def create_nested_objects(self, created_objects, validated_data):
        """
        Метод для создания связанных объектов.
        Должен быть реализован в наследуемом классе.
        """
        raise NotImplementedError('Определите create_nested_objects для NestedCreateUpdateMixin')

    def _create_or_update_nested_objects(self, parent_obj, nested_data):
        nested_manager = getattr(parent_obj, self.nested_objects_name)
        existing_objects = {obj.id: obj for obj in nested_manager.all()}
        for obj_data in nested_data:
            obj_id = obj_data.get('id', None)
            if obj_id and obj_id in existing_objects:
                existing_objects[obj_id].__class__.objects.filter(id=obj_id).update(**obj_data)
                existing_objects.pop(obj_id)
            else:
                new_obj = self.create_nested_objects(parent_obj, obj_data)
                existing_objects.pop(new_obj.id, None)

        for obj in existing_objects.values():
            obj.delete()


class CreateUpdateSerializerMixin(serializers.ModelSerializer):
    """
    Миксин для сериализаторов, реализующий логику создания
    и обновления связанных объектов в показателях отчета.
    """
    objects_name = None
    nested_objects_name = None

    class Meta:
        model = None

    def create(self, validated_data):
        received_objects = validated_data.pop(self.objects_name, [])
        created_objects = self.Meta.model.objects.create(**validated_data)
        self._create_or_update_objects(created_objects, received_objects)
        return created_objects

    def update(self, instance, validated_data):
        received_objects = validated_data.pop(self.objects_name, [])
        instance = super().update(instance, validated_data)
        self._create_or_update_objects(instance, received_objects)
        return instance

    def create_objects(self, created_objects, validated_data):
        """
        Метод для создания связанных объектов.
        Должен быть реализован в наследуемом классе.
        """
        raise NotImplementedError('Определите create_objects для CreateUpdateSerializerMixin')

    def _create_or_update_objects(self, created_objects, received_objects):
        existing_objects = {obj.id: obj for obj in getattr(created_objects, self.objects_name).all()}
        for obj_data in received_objects:
            print(f'self.nested_objects_name = {self.nested_objects_name}')
            if self.nested_objects_name:
                nested_data = obj_data.pop(self.nested_objects_name, [])
            obj_id = obj_data.get('id', None)
            if obj_id and obj_id in existing_objects:
                existing_objects[obj_id].__class__.objects.filter(id=obj_id).update(**obj_data)
                if hasattr(self, '_create_or_update_nested_objects') and self.nested_objects_name:
                    obj_instance = existing_objects[obj_id].__class__.objects.get(id=obj_id)
                    self._create_or_update_nested_objects(obj_instance, nested_data)
                existing_objects.pop(obj_id)
            else:
                new_obj = self.create_objects(created_objects, obj_data)
                if hasattr(self, '_create_or_update_nested_objects') and self.nested_objects_name:
                    self._create_or_update_nested_objects(new_obj, nested_data)
        for obj in existing_objects.values():
            obj.delete()


class BaseRSerializer(serializers.ModelSerializer):
    """Базовый класс для сериализаторов шаблона RegionalR<int>Serializer.

    - regional_version: Данные последней версии отчета, отправленного региональным штабом.
    - district_version: Данные последней версии отчета, отправленные (измененные) окружным штабом.
    - central_version: Данные последней версии отчета, отправленные (измененные) центральным штабом.
    - rejecting_reasons: Причины отклонения отчета центральным штабом, если таковые имеются.
    """
    regional_version = serializers.SerializerMethodField()
    district_version = serializers.SerializerMethodField()
    central_version = serializers.SerializerMethodField()
    rejecting_reasons = serializers.SerializerMethodField()

    class Meta:
        model = None
        fields = (
            'id',
            'regional_headquarter',
            'is_sent',
            'verified_by_chq',
            'verified_by_dhq',
            'created_at',
            'updated_at',
            'score',
            'regional_version',
            'district_version',
            'central_version',
            'rejecting_reasons'
        )
        read_only_fields = (
            'id',
            'regional_headquarter',
            'is_sent',
            'verified_by_chq',
            'verified_by_dhq',
            'created_at',
            'updated_at',
            'score',
        )

    def get_report_number(self):
        return get_report_number_by_class_name(self)

    def validate(self, attrs):
        action = self.context.get('action')
        regional_headquarter = self.context.get('regional_hq')
        report = self.__class__.Meta.model.objects.filter(regional_headquarter=regional_headquarter).last()

        if action == 'create':
            if report and hasattr(report, 'verified_by_chq') and hasattr(report, 'verified_by_dhq'):
                if report.verified_by_chq is not False:
                    raise serializers.ValidationError(REPORT_EXISTS_MESSAGE)

        elif action == 'update':
            if report and report.is_sent is True:
                raise serializers.ValidationError(REPORT_SENT_MESSAGE)

        return super().validate(attrs)

    def get_regional_version(self, obj):
        try:
            return RVerificationLog.objects.get(
                regional_headquarter=obj.regional_headquarter,
                is_regional_data=True,
                report_number=self.get_report_number(),
                report_id=obj.id
            ).data
        except RVerificationLog.DoesNotExist:
            return

    def get_district_version(self, obj):
        try:
            return RVerificationLog.objects.get(
                regional_headquarter=obj.regional_headquarter,
                is_district_data=True,
                report_number=self.get_report_number(),
                report_id=obj.id
            ).data
        except RVerificationLog.DoesNotExist:
            return

    def get_central_version(self, obj):
        log_obj = RVerificationLog.objects.filter(
            regional_headquarter=obj.regional_headquarter,
            is_central_data=True,
            report_number=self.get_report_number(),
            report_id=obj.id
        ).last()
        return log_obj.data if log_obj else None

    def get_rejecting_reasons(self, obj):
        chq_rejecting_log = CHqRejectingLog.objects.filter(
            report_number=self.get_report_number(),
            report_id=obj.id,
        ).last()
        return chq_rejecting_log.reasons if chq_rejecting_log else chq_rejecting_log


class BaseLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = (
            'id',
            'link'
        )
        read_only_fields = ('id',)


class BaseEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = None
        fields = (
            'id',
            'participants_number',
            'start_date',
            'end_date',
            'regulations',
        )
        read_only_fields = ('id',)


class RegionalR1Serializer(BaseRSerializer, FileScanSizeSerializerMixin):
    class Meta:
        model = RegionalR1
        fields = (
            BaseRSerializer.Meta.fields + FileScanSizeSerializerMixin.Meta.fields
            + ('comment', 'amount_of_money')
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


class RegionalR4LinkSerializer(BaseLinkSerializer):
    class Meta:
        model = RegionalR4Link
        fields = BaseLinkSerializer.Meta.fields + (
            'regional_r4_event',
        )
        read_only_fields = BaseLinkSerializer.Meta.read_only_fields + (
            'regional_r4_event',
        )


class RegionalR4EventSerializer(BaseEventSerializer):
    links = RegionalR4LinkSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = RegionalR4Event
        fields = BaseEventSerializer.Meta.fields + (
            'links',
            'regional_r4',
            'is_interregional',
        )
        read_only_fields = ('id', 'regional_r4',)


class RegionalR4Serializer(
    BaseRSerializer, CreateUpdateSerializerMixin, NestedCreateUpdateMixin
):
    events = RegionalR4EventSerializer(many=True, required=False, allow_null=True)

    objects_name = 'events'
    nested_objects_name = 'links'

    class Meta:
        model = RegionalR4
        fields = BaseRSerializer.Meta.fields + ('comment', 'events',)
        read_only_fields = BaseRSerializer.Meta.read_only_fields

    def create_objects(self, created_objects, event_data):
        return RegionalR4Event.objects.create(
            regional_r4=created_objects, **event_data
        )

    def create_nested_objects(self, parent_obj, obj_data):
        return RegionalR4Link.objects.create(
            regional_r4_event=parent_obj, **obj_data
        )


class RegionalR5LinkSerializer(BaseLinkSerializer):
    class Meta:
        model = RegionalR5Link
        fields = BaseLinkSerializer.Meta.fields + (
            'regional_r5_event',
        )
        read_only_fields = BaseLinkSerializer.Meta.read_only_fields + (
            'regional_r5_event',
        )


class RegionalR5EventSerializer(BaseEventSerializer):
    links = RegionalR5LinkSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = RegionalR5Event
        fields = BaseEventSerializer.Meta.fields + (
            'links',
            'regional_r5',
            'ro_participants_number'
        )
        read_only_fields = ('id', 'regional_r5')


class RegionalR5Serializer(
    BaseRSerializer, CreateUpdateSerializerMixin, NestedCreateUpdateMixin
):
    events = RegionalR5EventSerializer(many=True, required=False, allow_null=True)

    objects_name = 'events'
    nested_objects_name = 'links'

    class Meta:
        model = RegionalR5
        fields = BaseRSerializer.Meta.fields + ('comment', 'events',)
        read_only_fields = BaseRSerializer.Meta.read_only_fields

    def create_objects(self, created_objects, event_data):
        return RegionalR5Event.objects.create(
            regional_r5=created_objects, **event_data
        )

    def create_nested_objects(self, parent_obj, obj_data):
        return RegionalR5Link.objects.create(
            regional_r5_event=parent_obj, **obj_data
        )


class BaseRegionalR6Serializer(BaseRSerializer, CreateUpdateSerializerMixin):
    objects_name = 'links'

    class Meta:
        link_model = None
        model = None
        fields = (
            BaseRSerializer.Meta.fields
            + ('number_of_members', 'links', 'comment')
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


r6_serializers_factory = RSerializerFactory(
    models=r6_models_factory.models,
    base_r_serializer=BaseRegionalR6Serializer
)
r6_serializers_factory.create_serializer_classes()


class BaseRegionalR7Serializer(BaseRSerializer, CreateUpdateSerializerMixin, FileScanSizeSerializerMixin):
    objects_name = 'links'

    class Meta:
        link_model = None
        model = None
        fields = (
            BaseRSerializer.Meta.fields
            + ('prize_place', 'document', 'links', 'comment')
            + FileScanSizeSerializerMixin.Meta.fields
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


r7_serializers_factory = RSerializerFactory(
    models=r7_models_factory.models,
    base_r_serializer=BaseRegionalR7Serializer
)
r7_serializers_factory.create_serializer_classes()


class BaseRegionalR9Serializer(BaseRSerializer, CreateUpdateSerializerMixin, FileScanSizeSerializerMixin):
    objects_name = 'links'

    class Meta:
        link_model = None
        model = None
        fields = (
            BaseRSerializer.Meta.fields
            + ('event_happened', 'document', 'links')
            + FileScanSizeSerializerMixin.Meta.fields
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


r9_serializers_factory = RSerializerFactory(
    r9_models_factory.models,
    BaseRegionalR9Serializer
)
r9_serializers_factory.create_serializer_classes()


class BaseRegionalR10Serializer(BaseRSerializer, CreateUpdateSerializerMixin, FileScanSizeSerializerMixin):
    objects_name = 'links'

    class Meta:
        link_model = None
        model = None
        fields = (
            BaseRSerializer.Meta.fields
            + ('event_happened', 'document', 'links')
            + FileScanSizeSerializerMixin.Meta.fields
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


class RegionalR101LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR101Link
        fields = ('id', 'regional_r101', 'link')
        read_only_fields = ('id', 'regional_r101')


class RegionalR101Serializer(BaseRegionalR10Serializer, CreateUpdateSerializerMixin):
    links = RegionalR101LinkSerializer(many=True, allow_null=True, required=False)

    class Meta:
        link_model = RegionalR101Link
        model = RegionalR101
        fields = BaseRSerializer.Meta.fields + BaseRegionalR10Serializer.Meta.fields
        read_only_fields = BaseRSerializer.Meta.read_only_fields + BaseRegionalR10Serializer.Meta.read_only_fields

    def create_objects(self, created_objects, link_data):
        return RegionalR101Link.objects.create(
            regional_r101=created_objects, **link_data
        )


class RegionalR102LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR102Link
        fields = ('id', 'regional_r102', 'link')
        read_only_fields = ('id', 'regional_r102')


class RegionalR102Serializer(BaseRegionalR10Serializer, CreateUpdateSerializerMixin):
    links = RegionalR102LinkSerializer(many=True, allow_null=True, required=False)

    class Meta:
        link_model = RegionalR102Link
        model = RegionalR102
        fields = BaseRegionalR10Serializer.Meta.fields
        read_only_fields = BaseRegionalR10Serializer.Meta.read_only_fields

    def create_objects(self, created_objects, link_data):
        return RegionalR102Link.objects.create(
            regional_r102=created_objects, **link_data
        )


class RegionalR11Serializer(BaseRSerializer, FileScanSizeSerializerMixin):
    class Meta:
        model = RegionalR11
        fields = (
            BaseRSerializer.Meta.fields
            + FileScanSizeSerializerMixin.Meta.fields
            + ('comment', 'participants_number', 'scan_file')
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


class RegionalR12Serializer(BaseRSerializer, FileScanSizeSerializerMixin):
    class Meta:
        model = RegionalR12
        fields = (
            BaseRSerializer.Meta.fields
            + FileScanSizeSerializerMixin.Meta.fields
            + ('comment', 'amount_of_money', 'scan_file')
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


class RegionalR13Serializer(BaseRSerializer, FileScanSizeSerializerMixin):
    class Meta:
        model = RegionalR13
        fields = (
            BaseRSerializer.Meta.fields
            + FileScanSizeSerializerMixin.Meta.fields
            + ('comment', 'number_of_members', 'scan_file')
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


class RegionalR16LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR16Link
        fields = (
            'id',
            'regional_r16_project',
            'link'
        )
        read_only_fields = ('id', 'regional_r16_project',)


class RegionalR16ProjectSerializer(FileScanSizeSerializerMixin):
    links = RegionalR16LinkSerializer(many=True, allow_null=True, required=False)

    class Meta:
        model = RegionalR16Project
        fields = (
            'id',
            'regional_r16',
            'name',
            'project_scale',
            'regulations',
            'links'
        ) + FileScanSizeSerializerMixin.Meta.fields
        read_only_fields = ('id', 'regional_r16', )


class RegionalR16Serializer(BaseRSerializer, CreateUpdateSerializerMixin, NestedCreateUpdateMixin):
    projects = RegionalR16ProjectSerializer(many=True, allow_null=True, required=False)

    objects_name = 'projects'
    nested_objects_name = 'links'

    class Meta:
        model = RegionalR16
        fields = BaseRSerializer.Meta.fields + ('is_project', 'projects',)
        read_only_fields = BaseRSerializer.Meta.read_only_fields

    def create_objects(self, created_objects, project_data):
        return RegionalR16Project.objects.create(
            regional_r16=created_objects, **project_data
        )

    def create_nested_objects(self, parent_obj, obj_data):
        return RegionalR16Link.objects.create(
            regional_r16_project=parent_obj, **obj_data
        )


class RegionalR17Serializer(BaseRSerializer, FileScanSizeSerializerMixin):

    class Meta:
        model = RegionalR17
        fields = (
            BaseRSerializer.Meta.fields
            + FileScanSizeSerializerMixin.Meta.fields
            + ('scan_file', 'comment',)
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


class RegionalR18LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR18Link
        fields = (
            'id',
            'regional_r18_project',
            'link'
        )
        read_only_fields = ('id', 'regional_r18_project',)


class RegionalR18ProjectSerializer(FileScanSizeSerializerMixin):
    links = RegionalR18LinkSerializer(many=True, allow_null=True, required=False)

    class Meta:
        model = RegionalR18Project
        fields = (
            'id',
            'regional_r18',
            'file',
            'links'
        ) + FileScanSizeSerializerMixin.Meta.fields
        read_only_fields = ('id', 'regional_r18',)


class RegionalR18Serializer(CreateUpdateSerializerMixin, NestedCreateUpdateMixin):
    projects = RegionalR18ProjectSerializer(many=True, allow_null=True, required=False)

    objects_name = 'projects'
    nested_objects_name = 'links'

    class Meta:
        model = RegionalR18
        fields = (
            "id",
            "regional_headquarter",
            "created_at",
            "updated_at",
            "comment",
            "projects",
        )
        read_only_fields = (
            "id",
            "regional_headquarter",
            "created_at",
            "updated_at",
        )

    def create_objects(self, created_objects, project_data):
        return RegionalR18Project.objects.create(
            regional_r18=created_objects, **project_data
        )

    def create_nested_objects(self, parent_obj, obj_data):
        return RegionalR18Link.objects.create(
            regional_r18_project=parent_obj, **obj_data
        )


class RegionalR19Serializer(BaseRSerializer):
    class Meta:
        model = RegionalR19
        fields = BaseRSerializer.Meta.fields + ('employed_student_start', 'employed_student_end', 'comment',)
        read_only_fields = BaseRSerializer.Meta.read_only_fields


class EventNameSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class MassSendSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


# Список сериализаторов для генерации PDF-файла по 2-й части отчета
REPORTS_SERIALIZERS = [
    RegionalR1Serializer,
    RegionalR4Serializer,
    RegionalR5Serializer,
    RegionalR101Serializer,
    RegionalR102Serializer,
    RegionalR11Serializer,
    RegionalR12Serializer,
    RegionalR13Serializer,
    RegionalR16Serializer,
]
# REPORTS_SERIALIZERS.extend(r6_serializers_factory.serializers)

REPORTS_SERIALIZERS.extend(
    [
        serializer_class for serializer_name, serializer_class in r7_serializers_factory.serializers.items()
        if not serializer_name.endswith('Link')
    ]
)
REPORTS_SERIALIZERS.extend(
    [
        serializer_class for serializer_name, serializer_class in r9_serializers_factory.serializers.items()
        if not serializer_name.endswith('Link')
    ]
)
