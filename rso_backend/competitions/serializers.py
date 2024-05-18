from datetime import date

from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from competitions.models import (Q7, Q8, Q9, Q10, Q11, Q12,
                                 CompetitionApplications,
                                 CompetitionParticipants, Competitions,
                                 LinksQ7, LinksQ8, Q2DetachmentReport,
                                 Q5DetachmentReport, Q5EducatedParticipant,
                                 Q6DetachmentReport, Q7Report, Q8Report,
                                 Q9Report, Q10Report, Q11Report, Q12Report,
                                 Q13DetachmentReport, Q13EventOrganization,
                                 Q14DetachmentReport, Q14LaborProject,
                                 Q14Ranking, Q14TandemRanking,
                                 Q15DetachmentReport, Q15GrantWinner,
                                 Q16Report, Q17DetachmentReport, Q17EventLink,
                                 Q18DetachmentReport, Q19Report, Q20Report,
                                 QVerificationLog, ProfessionalCompetitionBlock, CreativeFestivalBlock,
                                 WorkingSemesterOpeningBlock, CommanderCommissionerSchoolBlock, SafetyWorkWeekBlock,
                                 PatrioticActionBlock, DemonstrationBlock, SpartakiadBlock)
from headquarters.models import Detachment
from headquarters.serializers import (BaseShortUnitSerializer,
                                      ShortDetachmentSerializer)
from users.short_serializers import ShortUserSerializer


class ShortDetachmentCompetitionSerializer(BaseShortUnitSerializer):
    area = serializers.CharField(source='area.name')

    class Meta:
        model = Detachment
        fields = BaseShortUnitSerializer.Meta.fields + (
            'area',
        )


class CompetitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competitions
        fields = '__all__'


class CompetitionApplicationsObjectSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer()
    junior_detachment = ShortDetachmentCompetitionSerializer()
    detachment = ShortDetachmentCompetitionSerializer()

    class Meta:
        model = CompetitionApplications
        fields = (
            'id',
            'competition',
            'junior_detachment',
            'detachment',
            'created_at',
            'is_confirmed_by_junior'
        )


class CompetitionApplicationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionApplications
        fields = (
            'id',
            'competition',
            'junior_detachment',
            'detachment',
            'created_at',
            'is_confirmed_by_junior'
        )
        read_only_fields = (
            'id',
            'created_at',
            'competition',
            'junior_detachment',
        )

    def validate(self, attrs):
        request = self.context.get('request')
        applications = CompetitionApplications.objects.all()
        participants = CompetitionParticipants.objects.all()
        if request.method == 'POST':
            MIN_DATE = (f'{settings.DATE_JUNIOR_SQUAD[2]}'
                        f'.{settings.DATE_JUNIOR_SQUAD[1]}.'
                        f'{settings.DATE_JUNIOR_SQUAD[0]} года')
            competition = self.context.get('competition')
            detachment = self.context.get('detachment')
            junior_detachment = self.context.get('junior_detachment')

            if detachment:
                if not request.data.get('junior_detachment'):
                    raise serializers.ValidationError(
                        f'- дата основания основания отряда ранее {MIN_DATE}'
                    )
                if detachment.founding_date >= date(
                    *settings.DATE_JUNIOR_SQUAD
                ):
                    raise serializers.ValidationError(
                        f'- отряд-наставник должен быть основан до {MIN_DATE}'
                    )
                if applications.filter(
                    competition=competition,
                    detachment=detachment
                ).exists() or participants.filter(
                    competition=competition,
                    detachment=detachment
                ).exists():
                    raise serializers.ValidationError(
                        'Вы уже подали заявку или участвуете в этом конкурсе'
                    )

            if junior_detachment.founding_date < date(
                *settings.DATE_JUNIOR_SQUAD
            ):
                raise serializers.ValidationError(
                    f'- дата основания отряда ранее {MIN_DATE}'
                )
            if applications.filter(
                competition=competition,
                junior_detachment=junior_detachment
                ).exists() or participants.filter(
                    competition=competition,
                    junior_detachment=junior_detachment
                    ).exists():
                raise serializers.ValidationError(
                    '- отряд уже подал заявку или участвует '
                    'в этом конкурсе'
                )
        return attrs


class ShortRegionalDetachmentCompetitionSerializer(
    ShortDetachmentCompetitionSerializer
):
    regional_headquarter_name = serializers.CharField(
        source='regional_headquarter.name'
    )

    class Meta:
        model = Detachment
        fields = ShortDetachmentCompetitionSerializer.Meta.fields + (
            'regional_headquarter_name',
        )


class CompetitionParticipantsObjectSerializer(serializers.ModelSerializer):
    detachment = ShortRegionalDetachmentCompetitionSerializer()
    junior_detachment = ShortRegionalDetachmentCompetitionSerializer()

    class Meta:
        model = CompetitionParticipants
        fields = (
            'id',
            'competition',
            'detachment',
            'junior_detachment',
            'created_at'
        )


class CompetitionParticipantsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionParticipants
        fields = (
            'id',
            'competition',
            'detachment',
            'junior_detachment',
            'created_at'
        )
        read_only_fields = (
            'id',
            'competition',
            'detachment',
            'junior_detachment',
            'created_at'
        )

    def validate(self, attrs):
        request = self.context.get('request')
        if request.method == 'POST':
            application = self.context.get('application')
            if (application.detachment and not
                    application.is_confirmed_by_junior):
                raise serializers.ValidationError(
                    'Заявка еще не подтверждена младшим отрядом.'
                )
        return attrs


class Q2DetachmentReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Q2DetachmentReport
        fields = (
            'id',
            'is_verified',
            'competition',
            'detachment',
            'commander_achievement',
            'commissioner_achievement',
            'commander_link',
            'commissioner_link'
        )
        read_only_fields = ('id', 'competition', 'detachment', 'is_verified')


class LinksQ7Serializer(
        serializers.ModelSerializer
):
    class Meta:
        model = LinksQ7
        fields = (
            'id',
            'link'
        )


class ShortQ7ReportSerializer(serializers.ModelSerializer):
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q7Report
        fields = (
            'id',
            'detachment',
            'competition'
        )


class Q7Serializer(
        serializers.ModelSerializer
):
    links = LinksQ7Serializer(
        many=True
    )
    detachment_report = ShortQ7ReportSerializer(read_only=True)

    class Meta:
        model = Q7
        fields = (
            'id',
            'certificate_scans',
            'event_name',
            'number_of_participants',
            'links',
            'is_verified',
            'detachment_report'
        )
        read_only_fields = (
            'id',
            'event_name',
            'detachment',
            'is_verified',
            'detachment_report'
        )

    def validate(self, attrs):
        request = self.context.get('request')
        links = request.data.get('links')
        if not links or len(links) == 0:
            raise serializers.ValidationError(
                {'links': 'Добавьте хотя бы одну ссылку на фотоотчет.'}
            )
        link_values = [link['link'] for link in links]
        if len(link_values) != len(set(link_values)):
            raise serializers.ValidationError(
                {'links': 'Указаны одинаковые ссылки на фотоотчет.'}
            )
        return attrs

    def update(self, instance, validated_data):
        links = validated_data.pop('links')
        if links:
            try:
                with transaction.atomic():
                    event = super().update(instance, validated_data)
                    event.links.all().delete()
                    serializer = (
                        LinksQ7Serializer(
                            many=True,
                            data=links,
                            context={'request': self.context.get('request'),
                                     'detachment_report': event.detachment_report,
                                     'event': event}
                        )
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save(event=event)
            except Exception as e:
                raise serializers.ValidationError(e)
        else:
            event = super().update(instance, validated_data)
        return event


class CreateQ7Serializer(
        serializers.ModelSerializer
):
    links = LinksQ7Serializer(
        many=True
    )

    class Meta:
        model = Q7
        fields = (
            'id',
            'event_name',
            'certificate_scans',
            'number_of_participants',
            'links',
            'is_verified',
            'detachment_report'
        )
        read_only_fields = (
            'id',
            'detachment',
            'is_verified',
            'detachment_report'
        )

    def validate(self, attrs):
        event = self.context.get('event')
        links = event.get('links')
        if not links:
            raise serializers.ValidationError(
                {"links": "Добавьте хотя бы одну ссылку на фотоотчет"}
            )
        if not event.get('event_name'):
            raise serializers.ValidationError(
                {'event_name': 'Укажите название мероприятия.'}
            )
        if not event.get('number_of_participants'):
            raise serializers.ValidationError(
                {'number_of_participants': 'Укажите количество участников.'}
            )
        if not links or len(links) == 0:
            raise serializers.ValidationError(
                {'links': 'Добавьте хотя бы одну ссылку на фотоотчет.'}
            )
        if self.Meta.model.objects.filter(
            detachment_report=self.context.get('detachment_report'),
            event_name=attrs.get('event_name')
        ).exists():
            raise serializers.ValidationError(
                {'event_name': 'Отчетность по этому мероприятию уже подана.'}
            )
        link_values = [link['link'] for link in links]
        if len(link_values) != len(set(link_values)):
            raise serializers.ValidationError(
                {'links': 'Указаны одинаковые ссылки.'}
            )
        return attrs

    def create(self, validated_data):
        links = validated_data.pop('links')
        try:
            with transaction.atomic():
                event = super().create(validated_data)
                serializer = (
                    LinksQ7Serializer(
                        many=True,
                        data=links,
                        context={'request': self.context.get('request'),
                                 'detachment_report': event.detachment_report,
                                 'event': event}
                    )
                )
                serializer.is_valid(raise_exception=True)
                serializer.save(event=event)
        except Exception as e:
            raise serializers.ValidationError(e)
        return event


class Q7ReportSerializer(
    serializers.ModelSerializer
):
    participation_data = Q7Serializer(many=True)
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q7Report
        fields = '__all__'


class LinksQ8Serializer(
        serializers.ModelSerializer
):
    class Meta:
        model = LinksQ8
        fields = (
            'id',
            'link'
        )


class ShortQ8ReportSerializer(
        serializers.ModelSerializer
):
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q8Report
        fields = (
            'id',
            'detachment',
            'competition'
        )


class Q8Serializer(
        serializers.ModelSerializer
):
    links = LinksQ8Serializer(
        many=True
    )
    detachment_report = ShortQ8ReportSerializer(read_only=True)

    class Meta:
        model = Q8
        fields = (
            'id',
            'certificate_scans',
            'event_name',
            'number_of_participants',
            'links',
            'is_verified',
            'detachment_report'
        )
        read_only_fields = (
            'id',
            'event_name',
            'detachment',
            'is_verified',
            'detachment_report'
        )

    def validate(self, attrs):
        request = self.context.get('request')
        links = request.data.get('links')
        if not links or len(links) == 0:
            raise serializers.ValidationError(
                {'links': 'Добавьте хотя бы одну ссылку на фотоотчет.'}
            )
        link_values = [link['link'] for link in links]
        if len(link_values) != len(set(link_values)):
            raise serializers.ValidationError(
                {'links': 'Указаны одинаковые ссылки на фотоотчет.'}
            )
        return attrs

    def update(self, instance, validated_data):
        links = validated_data.pop('links')
        if links:
            try:
                with transaction.atomic():
                    event = super().update(instance, validated_data)
                    event.links.all().delete()
                    serializer = (
                        LinksQ8Serializer(
                            many=True,
                            data=links,
                            context={'request': self.context.get('request'),
                                     'detachment_report': event.detachment_report,
                                     'event': event}
                        )
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save(event=event)
            except Exception as e:
                raise serializers.ValidationError(e)
        else:
            event = super().update(instance, validated_data)
        return event


class CreateQ8Serializer(
        serializers.ModelSerializer
):
    links = LinksQ8Serializer(
        many=True
    )

    class Meta:
        model = Q8
        fields = (
            'id',
            'event_name',
            'certificate_scans',
            'number_of_participants',
            'links',
            'is_verified',
            'detachment_report'
        )
        read_only_fields = (
            'id',
            'detachment',
            'is_verified',
            'detachment_report'
        )

    def validate(self, attrs):
        event = self.context.get('event')
        links = event.get('links')
        if not links:
            raise serializers.ValidationError(
                {"links": "Добавьте хотя бы одну ссылку на фотоотчет"}
            )
        if not event.get('event_name'):
            raise serializers.ValidationError(
                {'event_name': 'Укажите название мероприятия.'}
            )
        if not event.get('number_of_participants'):
            raise serializers.ValidationError(
                {'number_of_participants': 'Укажите количество участников.'}
            )
        if not links or len(links) == 0:
            raise serializers.ValidationError(
                {'links': 'Добавьте хотя бы одну ссылку на фотоотчет.'}
            )
        if self.Meta.model.objects.filter(
            detachment_report=self.context.get('detachment_report'),
            event_name=attrs.get('event_name')
        ).exists():
            raise serializers.ValidationError(
                {'event_name': 'Отчетность по этому мероприятию уже подана.'}
            )
        link_values = [link['link'] for link in links]
        if len(link_values) != len(set(link_values)):
            raise serializers.ValidationError(
                {'links': 'Указаны одинаковые ссылки.'}
            )
        return attrs

    def create(self, validated_data):
        links = validated_data.pop('links')
        try:
            with transaction.atomic():
                event = super().create(validated_data)
                serializer = (
                    LinksQ8Serializer(
                        many=True,
                        data=links,
                        context={'request': self.context.get('request'),
                                 'detachment_report': event.detachment_report,
                                 'event': event}
                    )
                )
                serializer.is_valid(raise_exception=True)
                serializer.save(event=event)
        except Exception as e:
            raise serializers.ValidationError(e)
        return event


class Q8ReportSerializer(
    serializers.ModelSerializer
):
    participation_data = Q8Serializer(many=True)
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q8Report
        fields = '__all__'


class ShortQ9ReportSerializer(
    serializers.ModelSerializer
):
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q9Report
        fields = (
            'id',
            'detachment',
            'competition'
        )


class Q9Serializer(
    serializers.ModelSerializer
):
    detachment_report = ShortQ9ReportSerializer(read_only=True)

    class Meta:
        model = Q9
        fields = (
            'id',
            'detachment_report',
            'certificate_scans',
            'event_name',
            'prize_place',
            'is_verified'
        )
        read_only_fields = (
            'id',
            'event_name',
            'detachment_report',
            'is_verified'
        )


class CreateQ9Serializer(
        serializers.ModelSerializer
):
    class Meta:
        model = Q9
        fields = (
            'id',
            'detachment_report',
            'event_name',
            'certificate_scans',
            'prize_place',
            'is_verified'
        )
        read_only_fields = (
            'id',
            'detachment_report',
            'is_verified'
        )

    def validate(self, attrs):
        prize_place = attrs.get('prize_place', None)
        if not attrs.get('event_name'):
            raise serializers.ValidationError(
                {'event_name': 'Укажите название мероприятия/конкурса.'}
            )
        if not prize_place:
            raise serializers.ValidationError(
                {'prize_place': 'Не указано призовое место.'}
            )
        if prize_place <= 0 or prize_place > 3:
            raise serializers.ValidationError(
                {'prize_place': 'Призовое место должно быть от 1 до 3.'}
            )
        if self.Meta.model.objects.filter(
            detachment_report=self.context.get('detachment_report'),
            event_name=attrs.get('event_name')
        ).exists():
            raise serializers.ValidationError(
                {'event_name':
                 'Отчетность по этому мероприятию/конкурсу уже подана.'}
            )
        return attrs


class Q9ReportSerializer(
    serializers.ModelSerializer
):
    participation_data = Q9Serializer(many=True)
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q9Report
        fields = '__all__'


class ShortQ10ReportSerializer(
    serializers.ModelSerializer
):
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q10Report
        fields = (
            'id',
            'detachment',
            'competition'
        )


class Q10Serializer(
    serializers.ModelSerializer
):
    detachment_report = ShortQ10ReportSerializer(read_only=True)

    class Meta:
        model = Q10
        fields = (
            'id',
            'detachment_report',
            'certificate_scans',
            'event_name',
            'prize_place',
            'is_verified'
        )
        read_only_fields = (
            'id',
            'event_name',
            'detachment_report',
            'is_verified'
        )


class CreateQ10Serializer(
        serializers.ModelSerializer
):
    class Meta:
        model = Q10
        fields = (
            'id',
            'detachment_report',
            'event_name',
            'certificate_scans',
            'prize_place',
            'is_verified'
        )
        read_only_fields = (
            'id',
            'detachment_report',
            'is_verified'
        )

    def validate(self, attrs):
        prize_place = attrs.get('prize_place', None)
        if not attrs.get('event_name'):
            raise serializers.ValidationError(
                {'event_name': 'Укажите название мероприятия/конкурса.'}
            )
        if not prize_place:
            raise serializers.ValidationError(
                {'prize_place': 'Не указано призовое место.'}
            )
        if prize_place <= 0 or prize_place > 3:
            raise serializers.ValidationError(
                {'prize_place': 'Призовое место должно быть от 1 до 3.'}
            )
        if self.Meta.model.objects.filter(
            detachment_report=self.context.get('detachment_report'),
            event_name=attrs.get('event_name')
        ).exists():
            raise serializers.ValidationError(
                {'event_name':
                 'Отчетность по этому мероприятию/конкурсу уже подана.'}
            )
        return attrs


class Q10ReportSerializer(
    serializers.ModelSerializer
):
    participation_data = Q10Serializer(many=True)
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q10Report
        fields = '__all__'


class ShortQ11ReportSerializer(
    serializers.ModelSerializer
):
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q11Report
        fields = (
            'id',
            'detachment',
            'competition'
        )


class Q11Serializer(
    serializers.ModelSerializer
):
    detachment_report = ShortQ11ReportSerializer(read_only=True)

    class Meta:
        model = Q11
        fields = (
            'id',
            'detachment_report',
            'certificate_scans',
            'event_name',
            'prize_place',
            'is_verified'
        )
        read_only_fields = (
            'id',
            'event_name',
            'detachment_report',
            'is_verified'
        )


class CreateQ11Serializer(
        serializers.ModelSerializer
):
    class Meta:
        model = Q11
        fields = (
            'id',
            'detachment_report',
            'event_name',
            'certificate_scans',
            'prize_place',
            'is_verified'
        )
        read_only_fields = (
            'id',
            'detachment_report',
            'is_verified'
        )

    def validate(self, attrs):
        prize_place = attrs.get('prize_place', None)
        if not attrs.get('event_name'):
            raise serializers.ValidationError(
                {'event_name': 'Укажите название мероприятия/конкурса.'}
            )
        if not prize_place:
            raise serializers.ValidationError(
                {'prize_place': 'Не указано призовое место.'}
            )
        if prize_place <= 0 or prize_place > 3:
            raise serializers.ValidationError(
                {'prize_place': 'Призовое место должно быть от 1 до 3.'}
            )
        if self.Meta.model.objects.filter(
            detachment_report=self.context.get('detachment_report'),
            event_name=attrs.get('event_name')
        ).exists():
            raise serializers.ValidationError(
                {'event_name':
                 'Отчетность по этому мероприятию/конкурсу уже подана.'}
            )
        return attrs


class Q11ReportSerializer(
    serializers.ModelSerializer
):
    participation_data = Q11Serializer(many=True)
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q11Report
        fields = '__all__'


class ShortQ12ReportSerializer(
    serializers.ModelSerializer
):
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q12Report
        fields = (
            'id',
            'detachment',
            'competition'
        )


class Q12Serializer(
    serializers.ModelSerializer
):
    detachment_report = ShortQ12ReportSerializer(read_only=True)

    class Meta:
        model = Q12
        fields = (
            'id',
            'detachment_report',
            'certificate_scans',
            'event_name',
            'prize_place',
            'is_verified'
        )
        read_only_fields = (
            'id',
            'event_name',
            'detachment_report',
            'is_verified'
        )


class CreateQ12Serializer(
        serializers.ModelSerializer
):
    class Meta:
        model = Q12
        fields = (
            'id',
            'detachment_report',
            'event_name',
            'certificate_scans',
            'prize_place',
            'is_verified'
        )
        read_only_fields = (
            'id',
            'detachment_report',
            'is_verified'
        )

    def validate(self, attrs):
        prize_place = attrs.get('prize_place', None)
        if not attrs.get('event_name'):
            raise serializers.ValidationError(
                {'event_name': 'Укажите название мероприятия/конкурса.'}
            )
        if not prize_place:
            raise serializers.ValidationError(
                {'prize_place': 'Не указано призовое место.'}
            )
        if prize_place <= 0 or prize_place > 3:
            raise serializers.ValidationError(
                {'prize_place': 'Призовое место должно быть от 1 до 3.'}
            )
        if self.Meta.model.objects.filter(
            detachment_report=self.context.get('detachment_report'),
            event_name=attrs.get('event_name')
        ).exists():
            raise serializers.ValidationError(
                {'event_name':
                 'Отчетность по этому мероприятию/конкурсу уже подана.'}
            )
        return attrs


class Q12ReportSerializer(
    serializers.ModelSerializer
):
    participation_data = Q12Serializer(many=True)
    detachment = ShortDetachmentCompetitionSerializer()
    competition = CompetitionSerializer()

    class Meta:
        model = Q12Report
        fields = '__all__'


class Q5EducatedParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Q5EducatedParticipant
        fields = (
            'id',
            'detachment_report',
            'name',
            'document',
            'is_verified'
        )
        read_only_fields = ('is_verified', 'detachment_report')


class Q5DetachmentReportReadSerializer(serializers.ModelSerializer):
    participants_data = serializers.SerializerMethodField()

    class Meta:
        model = Q5DetachmentReport
        fields = (
            'id',
            'competition',
            'detachment',
            'participants_data',
        )
        read_only_fields = ('competition', 'detachment')

    @staticmethod
    def get_participants_data(instance):
        participants_data = Q5EducatedParticipant.objects.filter(
            detachment_report=instance
        )
        return Q5EducatedParticipantSerializer(participants_data, many=True).data


class Q5DetachmentReportWriteSerializer(serializers.ModelSerializer):
    participants_data = serializers.ListField(
        child=Q5EducatedParticipantSerializer(),
        write_only=True
    )

    class Meta:
        model = Q5DetachmentReport
        fields = (
            'id',
            'competition',
            'detachment',
            'participants_data',
        )
        read_only_fields = ('competition', 'detachment')


class Q15GrantWinnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Q15GrantWinner
        fields = (
            'id',
            'detachment_report',
            'name',
            'status',
            'author_name',
            'competition_link',
            'prove_link',
            'is_verified'
        )
        read_only_fields = ('is_verified', 'detachment_report')


class Q15DetachmentReportWriteSerializer(serializers.ModelSerializer):
    grants_data = serializers.ListField(
        child=Q15GrantWinnerSerializer(),
        write_only=True
    )

    class Meta:
        model = Q15DetachmentReport
        fields = (
            'id',
            'competition',
            'detachment',
            'grants_data',
        )
        read_only_fields = ('competition', 'detachment')


class Q15DetachmentReportReadSerializer(serializers.ModelSerializer):
    grants_data = serializers.SerializerMethodField()

    class Meta:
        model = Q15DetachmentReport
        fields = (
            'id',
            'competition',
            'detachment',
            'grants_data',
        )
        read_only_fields = ('competition', 'detachment')

    @staticmethod
    def get_grants_data(instance):
        grants_data = Q15GrantWinner.objects.filter(
            detachment_report=instance
        )
        return Q15GrantWinnerSerializer(grants_data, many=True).data


class DemonstrationBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemonstrationBlock
        fields = (
            'first_may_demonstration',
            'first_may_demonstration_participants',
            'is_verified'
        )
        read_only_fields = ('is_verified',)


class PatrioticActionBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatrioticActionBlock
        fields = (
            'patriotic_action',
            'patriotic_action_participants',
            'is_verified'
        )
        read_only_fields = ('is_verified',)


class SafetyWorkWeekBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyWorkWeekBlock
        fields = (
            'safety_work_week',
            'is_verified'
        )
        read_only_fields = ('is_verified',)


class CommanderCommissionerSchoolBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommanderCommissionerSchoolBlock
        fields = (
            'commander_commissioner_school',
            'is_verified'
        )
        read_only_fields = ('is_verified',)


class WorkingSemesterOpeningBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingSemesterOpeningBlock
        fields = (
            'working_semester_opening',
            'working_semester_opening_participants',
            'is_verified'
        )
        read_only_fields = ('is_verified',)


class CreativeFestivalBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreativeFestivalBlock
        fields = (
            'creative_festival',
            'is_verified'
        )
        read_only_fields = ('is_verified',)


class ProfessionalCompetitionBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalCompetitionBlock
        fields = (
            'professional_competition',
            'is_verified'
        )
        read_only_fields = ('is_verified',)


class SpartakiadBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpartakiadBlock
        fields = (
            'spartakiad',
            'is_verified'
        )
        read_only_fields = ('is_verified',)


class Q6DetachmentReportSerializer(serializers.ModelSerializer):
    demonstration_block = DemonstrationBlockSerializer()
    patriotic_action_block = PatrioticActionBlockSerializer()
    safety_work_week_block = SafetyWorkWeekBlockSerializer()
    commander_commissioner_school_block = CommanderCommissionerSchoolBlockSerializer()
    working_semester_opening_block = WorkingSemesterOpeningBlockSerializer()
    creative_festival_block = CreativeFestivalBlockSerializer()
    professional_competition_block = ProfessionalCompetitionBlockSerializer()
    spartakiad_block = SpartakiadBlockSerializer()

    class Meta:
        model = Q6DetachmentReport
        fields = (
            'id',
            'competition',
            'detachment',
            'spartakiad_block',
            'demonstration_block',
            'patriotic_action_block',
            'safety_work_week_block',
            'commander_commissioner_school_block',
            'working_semester_opening_block',
            'creative_festival_block',
            'professional_competition_block'
        )
        read_only_fields = ('competition', 'detachment')


class Q13EventOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Q13EventOrganization
        fields = (
            'id',
            'event_type',
            'event_link',
            'detachment_report',
            'is_verified'
        )
        read_only_fields = ('is_verified', 'detachment_report')


class Q13DetachmentReportReadSerializer(serializers.ModelSerializer):
    organization_data = serializers.SerializerMethodField()

    class Meta:
        model = Q13DetachmentReport
        fields = ('id', 'competition', 'detachment', 'organization_data')

    @staticmethod
    def get_organization_data(instance):
        organized_events = Q13EventOrganization.objects.filter(detachment_report=instance)
        return Q13EventOrganizationSerializer(organized_events, many=True).data


class Q13DetachmentReportWriteSerializer(serializers.ModelSerializer):
    organization_data = serializers.ListField(
        child=Q13EventOrganizationSerializer(),
        write_only=True
    )

    class Meta:
        model = Q13DetachmentReport
        fields = (
            'id',
            'competition',
            'detachment',
            'organization_data',
        )
        read_only_fields = ('competition', 'detachment')


class Q14LaborProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Q14LaborProject
        fields = (
            'id',
            'lab_project_name',
            'amount',
            'detachment_report',
            'is_verified'
        )
        read_only_fields = ('id', 'is_verified', 'detachment_report')


class Q14DetachmentReportSerializer(serializers.ModelSerializer):

    q14_labor_projects = serializers.SerializerMethodField()

    class Meta:
        model = Q14DetachmentReport
        fields = (
            'id',
            'detachment',
            'competition',
            'q14_labor_projects'
        )
        read_only_fields = ('detachment', 'competition')

    def get_q14_labor_projects(self, instance):
        q14_labor_projects = Q14LaborProject.objects.filter(
            detachment_report=instance
        )
        return Q14LaborProjectSerializer(q14_labor_projects, many=True).data


class Q17EventLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Q17EventLink
        fields = (
            'id',
            'source_name',
            'link',
            'detachment_report',
            'is_verified'
        )
        read_only_fields = ('id', 'is_verified', 'detachment_report')


class Q17DetachmentReportSerializer(serializers.ModelSerializer):

    source_data = serializers.SerializerMethodField()

    class Meta:
        model = Q17DetachmentReport
        fields = (
            'id',
            'detachment',
            'competition',
            'source_data',
        )
        read_only_fields = ('is_verified', 'detachment', 'competition')

    def get_source_data(self, instance):
        source_data = Q17EventLink.objects.filter(
            detachment_report=instance
        )
        return Q17EventLinkSerializer(source_data, many=True).data


class Q18DetachmentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Q18DetachmentReport
        fields = (
            'id',
            'detachment',
            'competition',
            'participants_number',
            'is_verified'
        )
        read_only_fields = ('is_verified', 'detachment', 'competition',)

    def validate(self, attrs):
        competition = self.context.get('competition')
        detachment = self.context.get('detachment')
        if Q18DetachmentReport.objects.filter(
                competition=competition, detachment=detachment
        ).exists():
            raise serializers.ValidationError(
                {'error': 'Отчет по данному показателю уже существует'}
            )
        if not CompetitionParticipants.objects.filter(
                competition=competition,
                junior_detachment=detachment
        ).exists() and not CompetitionParticipants.objects.filter(
            competition=competition,
            detachment=detachment
        ).exists():
            raise serializers.ValidationError(
                {
                    'error': 'Отряд подающего пользователя не '
                             'участвует в конкурсе.'
                },
            )
        return attrs


class Q19DetachmenrtReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Q19Report
        fields = (
            'id',
            'detachment',
            'competition',
            'is_verified',
            'safety_violations'
        )
        read_only_fields = (
            'is_verified',
            'detachment',
            'competition'
        )

    def validate(self, attrs):
        request = self.context.get('request')
        if not attrs.get('safety_violations'):
            raise serializers.ValidationError(
                {'safety_violations': 'Не указано количество нарушений.'}
            )
        if attrs.get('safety_violations') not in ['Имеются', 'Отсутствуют']:
            raise serializers.ValidationError(
                {'safety_violations': 'Некорректное значение.'}
            )
        if request.method == 'POST':
            competition = self.context.get('competition')
            detachment = self.context.get('detachment')
            if Q19Report.objects.filter(
                    competition=competition, detachment=detachment
            ).exists():
                raise serializers.ValidationError(
                    {'error': 'Отчет по данному показателю уже существует'}
                )
        return attrs


class Q20ReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Q20Report
        fields = (
            'id',
            'detachment',
            'competition',
            'is_verified',
            'link_emblem',
            'link_emblem_img',
            'link_flag',
            'link_flag_img',
            'link_banner',
            'link_banner_img'
        )
        read_only_fields = (
            'is_verified',
            'detachment',
            'competition'
        )

    def validate(self, attrs):
        request = self.context.get('request')
        if request.method == 'POST':
            competition = self.context.get('competition')
            detachment = self.context.get('detachment')
            if Q20Report.objects.filter(
                    competition=competition, detachment=detachment
            ).exists():
                raise serializers.ValidationError(
                    {'error': 'Отчет по данному показателю уже существует'}
                )
        return attrs


class Q16ReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Q16Report
        fields = (
            'id',
            'detachment',
            'competition',
            'is_verified',
            'link_vk_commander',
            'link_vk_commissar',
            'vk_rso_number_subscribers',
            'link_vk_detachment',
            'vk_detachment_number_subscribers',
        )
        read_only_fields = (
            'is_verified',
            'detachment',
            'competition'
        )

    def validate(self, attrs):
        request = self.context.get('request')
        if request.method == 'POST':
            competition = self.context.get('competition')
            detachment = self.context.get('detachment')
            if Q16Report.objects.filter(
                    competition=competition, detachment=detachment
            ).exists():
                raise serializers.ValidationError(
                    {'error': 'Отчет по данному показателю уже существует'}
                )
            if attrs.get('vk_rso_number_subscribers') > detachment.members.count() + 1:
                raise serializers.ValidationError(
                    {'vk_rso_number_subscribers':
                     'Количество подписчиков больше, чем участников отряда'}
                )
        return attrs


class QVerificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = QVerificationLog
        fields = (
            'id',
            'competition_id',
            'q_number',
            'verified_detachment',
            'action',
            'timestamp'
        )

    def to_representation(self, instance):
        serialized_data = super().to_representation(instance)
        verifier, verified_detachment = (
            instance.verifier,
            instance.verified_detachment
        )

        if verifier:
            serialized_data['verifier'] = ShortUserSerializer(verifier).data
        if verified_detachment:
            serialized_data['verified_detachment'] = ShortDetachmentSerializer(verified_detachment).data

        return serialized_data
