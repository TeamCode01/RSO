from rest_framework import serializers

from api.utils import create_first_or_exception
from regional_competitions.constants import (REPORT_EXISTS_MESSAGE,
                                             REPORT_SENT_MESSAGE,
                                             STATISTICAL_REPORT_EXISTS_MESSAGE)
from regional_competitions.models import (CHqRejectingLog, RegionalR4, RegionalR5Event,
                                          RegionalR4Event, RegionalR4Link, RegionalR5,
                                          RVerificationLog, RegionalR5Link,
                                          StatisticalRegionalReport, RegionalR7, RegionalR7Place, RegionalR16Project,
                                          RegionalR16, RegionalR16Link, RegionalR101, RegionalR101Link,
                                          RegionalR102Link, RegionalR102)
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

    def create(self, validated_data):
        return create_first_or_exception(
            self,
            validated_data,
            StatisticalRegionalReport,
            STATISTICAL_REPORT_EXISTS_MESSAGE
        )


class NestedObjectsMixin:
    """
    Миксин для сериализаторов, которые реализуют логику
    создания и обновления для двух уровней вложенных объектов.
    """

    nested_objects_name = None

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
        pass

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
        read_only_fields = ('id', 'regional_r4')


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
        read_only_fields = ('id', 'regional_r4')


class RegionalR4Serializer(
    BaseRSerializer, CreateUpdateSerializerMixin, NestedObjectsMixin
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
            'regional_r5',
        )
        read_only_fields = BaseLinkSerializer.Meta.read_only_fields + (
            'regional_r5',
        )


class RegionalR5EventSerializer(BaseEventSerializer):
    links = RegionalR5LinkSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = RegionalR5Event
        fields = BaseEventSerializer.Meta.fields + (
            'links',
            'regional_r5',
            'is_interregional',
        )
        read_only_fields = ('id', 'regional_r5')


class RegionalR5Serializer(BaseRSerializer):
    projects = RegionalR5EventSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = RegionalR5
        fields = BaseRSerializer.Meta.fields + (
            'comment',
            'projects',
        )
        read_only_fields = BaseRSerializer.Meta.read_only_fields

    def create(self, validated_data):
        events_data = validated_data.pop('projects', [])
        regional_r5 = RegionalR5.objects.create(**validated_data)
        self._create_or_update_events(regional_r5, events_data)
        return regional_r5

    def update(self, instance, validated_data):
        events_data = validated_data.pop('projects', [])
        instance = super().update(instance, validated_data)
        self._create_or_update_events(instance, events_data)
        return instance

    def _create_or_update_events(self, regional_r5, events_data):
        existing_events = {event.id: event for event in regional_r5.events.all()}
        for event_data in events_data:
            links_data = event_data.pop('links', [])
            event_id = event_data.get('id', None)
            if event_id and event_id in existing_events:
                RegionalR5Event.objects.filter(id=event_id).update(**event_data)
                event = RegionalR5Event.objects.get(id=event_id)
                self._create_or_update_links(event, links_data)
                existing_events.pop(event_id)
            else:
                event = RegionalR5Event.objects.create(regional_r5=regional_r5, **event_data)
                self._create_or_update_links(event, links_data)
        for event in existing_events.values():
            event.delete()

    def _create_or_update_links(self, event, links_data):
        existing_links = {link.id: link for link in event.links.all()}
        for link_data in links_data:
            link_id = link_data.get('id', None)
            if link_id and link_id in existing_links:
                RegionalR4Link.objects.filter(id=link_id).update(**link_data)
                existing_links.pop(link_id)
            else:
                RegionalR4Link.objects.create(regional_r4_event=event, **link_data)
        for link in existing_links.values():
            link.delete()


class RegionalR7PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR7Place
        fields = (
            'id',
            'regional_r7',
            'place'
        )
        read_only_fields = ('id', 'regional_r7', )


class RegionalR7Serializer(BaseRSerializer, CreateUpdateSerializerMixin):
    places = RegionalR7PlaceSerializer(many=True)
    objects_name = 'places'

    class Meta:
        model = RegionalR7
        fields = BaseRSerializer.Meta.fields + ('places',)
        read_only_fields = BaseRSerializer.Meta.read_only_fields

    def create_objects(self, created_objects, place_data):
        return RegionalR7Place.objects.create(
            regional_r7=created_objects, **place_data
        )


class RegionalR16LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR16Link
        fields = (
            'id',
            'regional_r16_project',
            'link'
        )
        read_only_fields = ('id', 'regional_r16_project',)


class RegionalR16ProjectSerializer(serializers.ModelSerializer):
    links = RegionalR16LinkSerializer(many=True, allow_null=True)

    class Meta:
        model = RegionalR16Project
        fields = (
            'id',
            'regional_r16',
            'name',
            'project_scale',
            'regulations',
            'links'
        )
        read_only_fields = ('id', 'regional_r16', )


class RegionalR16Serializer(BaseRSerializer):
    projects = RegionalR16ProjectSerializer(many=True, allow_null=True, required=False)

    class Meta:
        model = RegionalR16
        fields = BaseRSerializer.Meta.fields + ('is_project', 'projects',)
        read_only_fields = BaseRSerializer.Meta.read_only_fields

    def create(self, validated_data):
        project_data = validated_data.pop('projects')
        regional_r16 = RegionalR16.objects.create(**validated_data)
        self._create_or_update_projects(regional_r16, project_data)
        return regional_r16

    def update(self, instance, validated_data):
        project_data = validated_data.pop('projects', [])
        instance = super().update(instance, validated_data)
        self._create_or_update_projects(instance, project_data)
        return instance

    def _create_or_update_projects(self, regional_r16, project_data):
        existing_projects = {project.id: project for project in regional_r16.projects.all()}
        for project in project_data:
            project_id = existing_projects.get('id', None)
            links = project.pop('links', [])
            if project_id and project_id in existing_projects:
                project = RegionalR16Project.objects.filter(id=project_id).update(**project)
                self._create_or_update_links(project, links)
                existing_projects.pop(project_id)
            else:
                project = RegionalR16Project.objects.create(regional_r16=regional_r16, **project)
                self._create_or_update_links(project, links)
        for link in existing_projects.values():
            link.delete()

    def _create_or_update_links(self, project, links_data):
        existing_links = {link.id: link for link in project.links.all()}
        for link_data in links_data:
            link_id = link_data.get('id', None)
            if link_id and link_id in existing_links:
                RegionalR16Link.objects.filter(id=link_id).update(**link_data)
                existing_links.pop(link_id)
            else:
                RegionalR16Link.objects.create(regional_r16_project=project, **link_data)
        for link in existing_links.values():
            link.delete()


class BaseRegionalR10Serializer(BaseRSerializer):
    class Meta:
        link_model = None
        model = None
        fields = BaseRSerializer.Meta.fields + ('event_happened', 'document', 'links')
        read_only_fields = BaseRSerializer.Meta.read_only_fields

    def create(self, validated_data):
        links = validated_data.pop('links')
        regional_r = self.__class__.Meta.model.objects.create(**validated_data)
        self._create_or_update_links(regional_r, links)
        return regional_r

    def update(self, instance, validated_data):
        links = validated_data.pop('links', [])
        instance = super().update(instance, validated_data)
        self._create_or_update_links(instance, links)
        return instance

    def _create_or_update_links(self, regional_r, links):
        existing_links = {link.id: link for link in regional_r.links.all()}
        for link in links:
            link_id = links.get('id', None)
            if link_id and link_id in existing_links:
                self.__class__.Meta.link_model.objects.filter(id=link_id).update(**link)
                existing_links.pop(link_id)
            else:
                self.__class__.Meta.link_model.objects.create(regional_r16=regional_r, **link)
        for link in existing_links.values():
            link.delete()


class RegionalR101LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR101Link
        fields = ('id', 'regional_r101', 'link')
        read_only_fields = ('id', 'regional_r101')


class RegionalR101Serializer(BaseRegionalR10Serializer):
    links = RegionalR101LinkSerializer(many=True, allow_null=True, required=False)

    class Meta:
        link_model = RegionalR101Link
        model = RegionalR101
        fields = BaseRegionalR10Serializer.Meta.fields
        read_only_fields = BaseRegionalR10Serializer.Meta.read_only_fields


class RegionalR102LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR102Link
        fields = ('id', 'regional_r102', 'link')
        read_only_fields = ('id', 'regional_r102')


class RegionalR102Serializer(BaseRegionalR10Serializer):
    links = RegionalR102LinkSerializer(many=True, allow_null=True, required=False)

    class Meta:
        link_model = RegionalR102Link
        model = RegionalR102
        fields = BaseRegionalR10Serializer.Meta.fields
        read_only_fields = BaseRegionalR10Serializer.Meta.read_only_fields
