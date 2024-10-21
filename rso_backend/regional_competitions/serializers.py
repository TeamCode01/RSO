import os
from datetime import datetime
from django.db import models
from django.http import QueryDict
from rest_framework import serializers

from django.db import transaction
from headquarters.serializers import ShortRegionalHeadquarterSerializer
from regional_competitions.constants import (CONVERT_TO_MB, REPORT_EXISTS_MESSAGE,
                                             REPORT_SENT_MESSAGE, ROUND_2_SIGNS,
                                             STATISTICAL_REPORT_EXISTS_MESSAGE)
from regional_competitions.factories import RSerializerFactory
from regional_competitions.models import (CHqRejectingLog, DumpStatisticalRegionalReport, RegionalR1, RegionalR18,
                                          RegionalR18Link, RegionalR18Project, RegionalR2,
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
                                          r6_models_factory, r9_models_factory, AdditionalStatistic)
from regional_competitions.utils import get_report_number_by_class_name


class DumpStatisticalRegionalReportSerializer(serializers.ModelSerializer):
    regional_headquarter = ShortRegionalHeadquarterSerializer(read_only=True)

    class Meta:
        model = DumpStatisticalRegionalReport
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
            'employed_so_poo',
            'employed_so_oovo',
            'employed_ro_rso'
        )


class AdditionalStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalStatistic
        fields = ('name', 'value',)
        read_only_fields = ('id', 'statistical_report')


class StatisticalRegionalReportSerializer(serializers.ModelSerializer):
    additional_statistics = AdditionalStatisticSerializer(required=False, allow_null=True, many=True)
    regional_headquarter = ShortRegionalHeadquarterSerializer(read_only=True)

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
            'employed_so_poo',
            'employed_so_oovo',
            'employed_ro_rso',
            'additional_statistics',
        )
        read_only_fields = ('id', 'regional_headquarter')
        extra_kwargs = {
            'id': {'read_only': True},
            'regional_headquarter': {
                'help_text': 'ID регионального штаба для которого создается или запрашивается отчет.'
            },
        }

    def create(self, validated_data):
        regional_headquarter = validated_data.get('regional_headquarter')

        if StatisticalRegionalReport.objects.filter(regional_headquarter=regional_headquarter).exists():
            raise serializers.ValidationError({'non_field_errors': STATISTICAL_REPORT_EXISTS_MESSAGE})

        additional_statistics_data = validated_data.pop('additional_statistics', None)

        with transaction.atomic():
            report = StatisticalRegionalReport.objects.create(**validated_data)

            if additional_statistics_data:
                for statistic_data in additional_statistics_data:
                    AdditionalStatistic.objects.create(statistical_report=report, **statistic_data)

        return report

    def update(self, instance, validated_data):
        additional_statistics_data = validated_data.pop('additional_statistics', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if additional_statistics_data is not None:
            instance.additional_statistics.all().delete()

            for statistic_data in additional_statistics_data:
                AdditionalStatistic.objects.create(statistical_report=instance, **statistic_data)

        return instance


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
        if check_file and hasattr(check_file, 'path'):
            file_path = check_file.path
            if os.path.exists(file_path):
                try:
                    return round(check_file.size / CONVERT_TO_MB, ROUND_2_SIGNS)
                except (FileNotFoundError, OSError):
                    return None
            else:
                return None
        return None

    def get_file_type(self, obj):
        file_field_name = self.get_file_field()
        if not file_field_name:
            return None
        check_file = getattr(obj, file_field_name)
        if check_file and hasattr(check_file, 'name'):
            try:
                return check_file.name.split('.')[-1]
            except (FileNotFoundError, OSError):
                return None
        return None



class EmptyAsNoneMixin:
    """
    Миксин для сериализаторов с полями типа FileField, где при отправке 
    с multipart/form-data требуется обработка пустых строк "" как None (null).
    """

    def treat_empty_string_as_none(self, data):
        """
        Рекурсивно обрабатывает словарь, заменяя пустые строки на None.
        """
        if isinstance(data, QueryDict):
            data = data.copy()

        for key, val in data.items():
            if val == '':
                data[key] = None
            elif isinstance(val, dict):
                data[key] = self.treat_empty_string_as_none(val)
            elif isinstance(val, list):
                data[key] = [self.treat_empty_string_as_none(item) if isinstance(item, dict) else item for item in val]

        return data

    def to_internal_value(self, data):
        """
        Переопределяем to_internal_value для обработки пустых строк как None перед валидацией.
        """
        return super().to_internal_value(self.treat_empty_string_as_none(data))


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
        """
        Метод для создания или обновления связанных объектов (events, projects, etc.),
        а также вложенных объектов. Если объект с указанным id существует, он обновляется, 
        если нет — создается новый объект. Если файл (например, scan_file) не передан, 
        используется существующий файл. Старые объекты удаляются, если их нет в новых данных.

        Логика работы метода:
        
        1. Создаем словарь с существующими объектами, сопоставляя их по id.
        2. Проходим по каждому объекту из новых данных:
            - Если объект содержит id и он есть в базе:
                - Обновляем объект, сохраняя файлы, если они не были переданы заново.
                - Обновляем вложенные объекты, если они есть.
                - Удаляем этот объект из списка существующих, чтобы в конце не удалить его.
            
            - Если id не передан (новый объект):
                - Пытаемся сопоставить с существующим объектом по порядку (берем первый 
                из оставшихся объектов).
                - Используем файлы из сопоставленного объекта, если они не были переданы.
                - Создаем новый объект с данными.
                - Обновляем вложенные объекты для нового объекта, если они есть.
                - Удаляем сопоставленный объект, так как он был заменен новым.
        
        3. В конце удаляем все оставшиеся объекты, которые не были обновлены или заменены.
        """
        existing_objects = {obj.id: obj for obj in getattr(created_objects, self.objects_name).all()}

        for obj_data in received_objects:
            obj_id = obj_data.get('id', None)

            if self.nested_objects_name:
                nested_data = obj_data.pop(self.nested_objects_name, [])

            if obj_id and obj_id in existing_objects:
                obj_instance = existing_objects[obj_id]

                for field in obj_instance._meta.fields:
                    if isinstance(field, models.FileField) and field.name not in obj_data:
                        obj_data[field.name] = getattr(obj_instance, field.name)

                existing_objects[obj_id].__class__.objects.filter(id=obj_id).update(**obj_data)

                if hasattr(self, '_create_or_update_nested_objects') and self.nested_objects_name:
                    obj_instance = existing_objects[obj_id].__class__.objects.get(id=obj_id)
                    self._create_or_update_nested_objects(obj_instance, nested_data)

                existing_objects.pop(obj_id)

            else:
                matched_obj = None
                if existing_objects:
                    matched_obj = list(existing_objects.values())[0]

                    for field in matched_obj._meta.fields:
                        if isinstance(field, models.FileField) and field.name not in obj_data:
                            obj_data[field.name] = getattr(matched_obj, field.name)

                new_obj = self.create_objects(created_objects, obj_data)

                if hasattr(self, '_create_or_update_nested_objects') and self.nested_objects_name:
                    self._create_or_update_nested_objects(new_obj, nested_data)

                if matched_obj:
                    existing_objects.pop(matched_obj.id, None)

                    matched_obj.delete()

        for obj in existing_objects.values():
            obj.delete()


class ReportExistsValidationMixin:
    def validate(self, data):
        if self.context.get('action') == 'create':
            user = self.context['request'].user
            if self.Meta.model.objects.filter(regional_headquarter__commander=user).exists():
                raise serializers.ValidationError(REPORT_EXISTS_MESSAGE)
        return data


class BaseRSerializer(EmptyAsNoneMixin, serializers.ModelSerializer):
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


class BaseEventSerializer(FileScanSizeSerializerMixin):
    class Meta:
        model = None
        fields = (
                     'id',
                     'participants_number',
                     'start_date',
                     'end_date',
                     'regulations',
                 ) + FileScanSizeSerializerMixin.Meta.fields
        read_only_fields = ('id',)

    def to_internal_value(self, data):
        print(f"Original data: {data}")

        if 'is_interregional' in data:
            data['is_interregional'] = True if data['is_interregional'].lower() == 'true' else False

        for date_field in ['start_date', 'end_date']:
            if date_field in data:
                try:
                    print(f"Parsing date field: {date_field} with value {data[date_field]}")
                    data[date_field] = datetime.strptime(data[date_field], '%Y-%m-%d').date()
                except ValueError:
                    raise serializers.ValidationError({
                        date_field: 'Неправильный формат date. Используйте формат: YYYY-MM-DD.'
                    })

        print(f"Modified data: {data}")
        return super().to_internal_value(data)


class RegionalR1Serializer(BaseRSerializer, FileScanSizeSerializerMixin):
    class Meta:
        model = RegionalR1
        fields = (
                BaseRSerializer.Meta.fields + FileScanSizeSerializerMixin.Meta.fields
                + ('comment', 'scan_file', 'amount_of_money')
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields


class RegionalR2Serializer(serializers.ModelSerializer):
    """Сериализатор используется в выгрузках отчетов."""

    class Meta:
        model = RegionalR2
        fields = (
            'id',
            'regional_headquarter',
            'created_at',
            'updated_at',
            'score',
            'full_time_students'
        )
        read_only_fields = (
            'id',
            'regional_headquarter',
            'created_at',
            'updated_at',
            'score',
        )


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
            'name'
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
            'ro_participants_number',
            'name'
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


# class BaseRegionalR7Serializer(BaseRSerializer, CreateUpdateSerializerMixin, FileScanSizeSerializerMixin):
#     objects_name = 'links'
#
#     class Meta:
#         link_model = None
#         model = None
#         fields = (
#             BaseRSerializer.Meta.fields
#             + ('prize_place', 'document', 'links', 'comment')
#             + FileScanSizeSerializerMixin.Meta.fields
#         )
#         read_only_fields = BaseRSerializer.Meta.read_only_fields
#
#
# r7_serializers_factory = RSerializerFactory(
#     models=r7_models_factory.models,
#     base_r_serializer=BaseRegionalR7Serializer
# )
# r7_serializers_factory.create_serializer_classes()


class BaseRegionalR9Serializer(BaseRSerializer, CreateUpdateSerializerMixin, FileScanSizeSerializerMixin):
    objects_name = 'links'

    class Meta:
        link_model = None
        model = None
        fields = (
                BaseRSerializer.Meta.fields
                + ('comment', 'event_happened', 'document', 'links')
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
                + ('comment', 'event_happened', 'document', 'links')
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
        read_only_fields = ('id', 'regional_r16',)


class RegionalR16Serializer(BaseRSerializer, CreateUpdateSerializerMixin, NestedCreateUpdateMixin):
    projects = RegionalR16ProjectSerializer(many=True, allow_null=True, required=False)

    objects_name = 'projects'
    nested_objects_name = 'links'

    class Meta:
        model = RegionalR16
        fields = BaseRSerializer.Meta.fields + ('is_project', 'projects', 'comment')
        read_only_fields = BaseRSerializer.Meta.read_only_fields

    def create_objects(self, created_objects, project_data):
        return RegionalR16Project.objects.create(
            regional_r16=created_objects, **project_data
        )

    def create_nested_objects(self, parent_obj, obj_data):
        return RegionalR16Link.objects.create(
            regional_r16_project=parent_obj, **obj_data
        )


class RegionalR17Serializer(
    EmptyAsNoneMixin, ReportExistsValidationMixin, FileScanSizeSerializerMixin, serializers.ModelSerializer
):
    class Meta:
        model = RegionalR17
        fields = (
                     'id',
                     'regional_headquarter',
                     'scan_file',
                     'comment',
                 ) + FileScanSizeSerializerMixin.Meta.fields
        read_only_fields = (
            'id',
            'regional_headquarter',
        )


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


class RegionalR18Serializer(
    EmptyAsNoneMixin, ReportExistsValidationMixin, CreateUpdateSerializerMixin, NestedCreateUpdateMixin
):
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


class RegionalR19Serializer(ReportExistsValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = RegionalR19
        fields = (
            'id',
            'regional_headquarter',
            'employed_student_start',
            'employed_student_end',
            'comment',
        )
        read_only_fields = (
            'id',
            'regional_headquarter',
        )


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
]

REPORTS_SERIALIZERS.extend(
    [
        serializer_class for serializer_name, serializer_class in r6_serializers_factory.serializers.items()
        if not serializer_name.endswith('Link')
    ]
)

# REPORTS_SERIALIZERS.extend(
#     [
#         serializer_class for serializer_name, serializer_class in r7_serializers_factory.serializers.items()
#         if not serializer_name.endswith('Link')
#     ]
# )
REPORTS_SERIALIZERS.extend(
    [
        serializer_class for serializer_name, serializer_class in r9_serializers_factory.serializers.items()
        if not serializer_name.endswith('Link')
    ]
)
REPORTS_SERIALIZERS.extend(
    [
        RegionalR101Serializer,
        RegionalR102Serializer,
        RegionalR11Serializer,
        RegionalR12Serializer,
        RegionalR13Serializer,
        RegionalR16Serializer,
        RegionalR17Serializer,
        RegionalR18Serializer,
        RegionalR19Serializer
    ]
)
