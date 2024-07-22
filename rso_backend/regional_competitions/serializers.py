from rest_framework import serializers

from api.utils import create_first_or_exception
from regional_competitions.constants import (REPORT_EXISTS_MESSAGE,
                                             REPORT_SENT_MESSAGE,
                                             STATISTICAL_REPORT_EXISTS_MESSAGE)
from regional_competitions.models import (CHqRejectingLog, RegionalR4,
                                          RegionalR4Event, RegionalR4Link,
                                          RVerificationLog,
                                          StatisticalRegionalReport)
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
            'employed_oop',
            'employed_smo',
            'employed_sservo',
            'employed_sses',
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
        fields = ('regional_version', 'district_version', 'central_version', 'rejecting_reasons')

    def get_report_number(self):
        return get_report_number_by_class_name(self)

    def validate(self, attrs):
        action = self.context.get('action')
        regional_headquarter = self.context.get('regional_hq')
        report = RegionalR4.objects.filter(regional_headquarter=regional_headquarter).last()

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


class RegionalR4LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalR4Link
        fields = (
            'id',
            'regional_r4_event',
            'link'
        )
        read_only_fields = ('id', 'regional_r4_event',)


class RegionalR4EventSerializer(serializers.ModelSerializer):
    links = RegionalR4LinkSerializer(many=True)

    class Meta:
        model = RegionalR4Event
        fields = (
            'id',
            'regional_r4',
            'participants_number',
            'start_date',
            'end_date',
            'regulations',
            'is_interregional',
            'links'
        )
        read_only_fields = ('id', 'regional_r4')

    def create(self, validated_data):
        links_data = validated_data.pop('links')
        event = RegionalR4Event.objects.create(**validated_data)
        self._create_or_update_links(event, links_data)
        return event

    def update(self, instance, validated_data):
        links_data = validated_data.pop('links', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._create_or_update_links(instance, links_data)
        return instance

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


class RegionalR4Serializer(BaseRSerializer):
    events = RegionalR4EventSerializer(many=True)

    class Meta:
        model = RegionalR4
        fields = (
            'id',
            'regional_headquarter',
            'is_sent',
            'verified_by_chq',
            'verified_by_dhq',
            'created_at',
            'updated_at',
            'score',
            'comment',
            'events',
        ) + BaseRSerializer.Meta.fields
        read_only_fields = (
            'id',
            'regional_headquarter',
            'is_sent',
            'verified_by_chq',
            'verified_by_dhq',
            'created_at',
            'updated_at',
            'score'
        )

    def create(self, validated_data):
        events_data = validated_data.pop('events', [])
        regional_r4 = create_first_or_exception(
            self,
            validated_data,
            RegionalR4,
            REPORT_EXISTS_MESSAGE
        )
        self._create_or_update_events(regional_r4, events_data)
        return regional_r4

    def update(self, instance, validated_data):
        events_data = validated_data.pop('events', [])
        instance = super().update(instance, validated_data)
        self._create_or_update_events(instance, events_data)
        return instance

    def _create_or_update_events(self, regional_r4, events_data):
        existing_events = {event.id: event for event in regional_r4.events.all()}
        for event_data in events_data:
            links_data = event_data.pop('links', [])
            event_id = event_data.get('id', None)
            if event_id and event_id in existing_events:
                RegionalR4Event.objects.filter(id=event_id).update(**event_data)
                event = RegionalR4Event.objects.get(id=event_id)
                self._create_or_update_links(event, links_data)
                existing_events.pop(event_id)
            else:
                event = RegionalR4Event.objects.create(regional_r4=regional_r4, **event_data)
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
