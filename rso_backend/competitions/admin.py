from django.contrib import admin

from competitions.models import (
    Q10, Q11, Q12, Q8, Q9, CompetitionApplications, CompetitionParticipants, Competitions,
    Q7, Q10Ranking, Q10Report, Q10TandemRanking, Q11Ranking, Q11Report, Q11TandemRanking, Q12Ranking, Q12Report,
    Q12TandemRanking, Q14DetachmentReport, Q14Ranking, Q14TandemRanking, Q17DetachmentReport, Q16Ranking, Q16Report,
    Q16TandemRanking, Q18Ranking, Q19Ranking,
    Q19Report, Q19TandemRanking, Q1Ranking, Q1Report, Q1TandemRanking,
    Q20Ranking, Q20Report, Q20TandemRanking, Q2DetachmentReport, Q2Ranking,
    Q7Ranking, Q7Report, Q13TandemRanking, Q18TandemRanking, Q13Ranking,
    Q7TandemRanking, Q8Ranking, Q8Report, Q8TandemRanking, Q9Ranking, Q9Report, Q9TandemRanking, Q2TandemRanking,
    Q17Ranking, Q17TandemRanking, Q5Ranking, Q5TandemRanking, Q15Rank, Q15TandemRank,
    Q5DetachmentReport, Q15DetachmentReport, Q6DetachmentReport, Q6Ranking, Q6TandemRanking,
    Q3Ranking, Q3TandemRanking, Q4Ranking, Q4TandemRanking, Q13DetachmentReport, Q5EducatedParticipant,
    Q13EventOrganization, Q15GrantWinner, Q18DetachmentReport, OverallTandemRanking, OverallRanking
)
from competitions.forms import (CompetitionApplicationsForm,
                                CompetitionParticipantsForm)


@admin.register(Competitions)
class CompetitionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    list_display = ('id',
                    'name',
                    'count_tandem_applications',
                    'count_start_applications',
                    'count_tandem_participants',
                    'count_start_participants',
                    'created_at')

    @admin.display(description='Тандем участников')
    def count_tandem_participants(self, obj):
        return obj.competition_participants.filter(
            detachment__isnull=False
        ).count()

    @admin.display(description='Старт участников')
    def count_start_participants(self, obj):
        return obj.competition_participants.filter(
            detachment__isnull=True
        ).count()

    @admin.display(description='Тандем заявок')
    def count_tandem_applications(self, obj):
        return obj.competition_applications.filter(
            detachment__isnull=False
        ).count()

    @admin.display(description='Старт заявок')
    def count_start_applications(self, obj):
        return obj.competition_applications.filter(
            detachment__isnull=True
        ).count()


@admin.register(CompetitionApplications)
class CompetitionApplicationsAdmin(admin.ModelAdmin):
    form = CompetitionApplicationsForm
    list_filter = ('competition__name',)
    search_fields = ('detachment__name',
                     'junior_detachment__name',
                     'competition__name',
                     'detachment__region__name',
                     'junior_detachment__region__name')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_display = ('id',
                    'get_region',
                    'is_tandem',
                    'detachment',
                    'junior_detachment',
                    'created_at')
    ordering = ('detachment', 'junior_detachment', 'created_at')

    @admin.display(description='Регион')
    def get_region(self, obj):
        return obj.junior_detachment.region
    get_region.admin_order_field = 'junior_detachment__region__name'

    @admin.display(description='Тип заявки')
    def is_tandem(self, obj):
        return 'Тандем' if obj.detachment is not None else 'Старт'


@admin.register(CompetitionParticipants)
class CompetitionParticipantsAdmin(admin.ModelAdmin):
    form = CompetitionParticipantsForm
    list_filter = ('competition__name',)
    search_fields = ('detachment__name',
                     'junior_detachment__name',
                     'competition__name',
                     'detachment__region__name',
                     'junior_detachment__region__name')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_display = ('id',
                    'get_region',
                    'is_tandem',
                    'detachment',
                    'junior_detachment',
                    'created_at')
    ordering = ('detachment', 'junior_detachment', 'created_at')

    @admin.display(description='Регион')
    def get_region(self, obj):
        return obj.junior_detachment.region
    get_region.admin_order_field = 'junior_detachment__region__name'

    @admin.display(description='Тип заявки')
    def is_tandem(self, obj):
        return 'Тандем' if obj.detachment is not None else 'Старт'


admin.site.register(Q2DetachmentReport)


class QBaseRankingAdmin(admin.ModelAdmin):
    list_display = ('id', 'competition_id', 'detachment', 'place')
    search_fields = ('detachment__name', 'place')


class QBaseTandemRankingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'competition_id', 'detachment', 'junior_detachment', 'place'
    )
    search_fields = ('detachment__name', 'junior_detachment__name', 'place')


@admin.register(OverallRanking)
class OverallRankingAdmin(admin.ModelAdmin):
    list_display = ('id', 'competition_id', 'detachment', 'places_sum', 'place')
    search_fields = ('detachment__name', 'place')


@admin.register(OverallTandemRanking)
class OverallTandemRankingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'competition_id', 'detachment', 'junior_detachment', 'places_sum', 'place'
    )
    search_fields = ('detachment__name', 'junior_detachment__name', 'place')


@admin.register(Q1Report)
class Q1ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')


@admin.register(Q1Ranking)
class Q1RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q1TandemRanking)
class Q1TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q2Ranking)
class Q2RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q2TandemRanking)
class Q2TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q3Ranking)
class Q3RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q3TandemRanking)
class Q3TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q4Ranking)
class Q4RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q4TandemRanking)
class Q4TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q5Ranking)
class Q5RankingAdmin(QBaseRankingAdmin):
    pass


class Q5EducatedParticipantInline(admin.TabularInline):
    model = Q5EducatedParticipant
    extra = 0


@admin.register(Q5DetachmentReport)
class Q5DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
        'june_15_detachment_members',
    )
    inlines = [Q5EducatedParticipantInline]
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'


@admin.register(Q5TandemRanking)
class Q5TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q6DetachmentReport)
class Q6DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
        'is_verified',
        'score',
        'first_may_demonstration',
        'first_may_demonstration_participants',
        'creative_festival',
        'patriotic_action',
        'patriotic_action_participants',
        'safety_work_week',
        'commander_commissioner_school',
        'working_semester_opening',
        'working_semester_opening_participants',
        'spartakiad',
        'professional_competition',
        'april_1_detachment_members',
    )
    list_filter = ('is_verified',)
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'


@admin.register(Q6Ranking)
class Q6RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q6TandemRanking)
class Q6TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q7)
class Q7Admin(admin.ModelAdmin):
    list_display = (
        'id', 'event_name', 'detachment_report', 'is_verified',
        'number_of_participants'
    )


@admin.register(Q7Report)
class Q7ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')


@admin.register(Q7Ranking)
class Q7RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q7TandemRanking)
class Q7TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q8)
class Q8Admin(admin.ModelAdmin):
    list_display = (
        'id', 'event_name', 'detachment_report', 'is_verified',
        'number_of_participants'
    )


@admin.register(Q8Report)
class Q8ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')


@admin.register(Q8Ranking)
class Q8RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q8TandemRanking)
class Q8TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q9)
class Q9Admin(admin.ModelAdmin):
    list_display = (
        'id', 'event_name', 'detachment_report', 'is_verified',
        'prize_place'
    )


@admin.register(Q9Report)
class Q9ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')


@admin.register(Q9Ranking)
class Q9RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q9TandemRanking)
class Q9TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q10)
class Q10Admin(admin.ModelAdmin):
    list_display = ('id', 'event_name', 'detachment_report',
                    'is_verified', 'prize_place')


@admin.register(Q10Report)
class Q10ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')


@admin.register(Q10Ranking)
class Q10RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q10TandemRanking)
class Q10TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q11)
class Q11Admin(admin.ModelAdmin):
    list_display = ('id', 'event_name', 'detachment_report',
                    'is_verified', 'prize_place')


@admin.register(Q11Report)
class Q11ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')


@admin.register(Q11Ranking)
class Q11RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q11TandemRanking)
class Q11TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q12)
class Q12Admin(admin.ModelAdmin):
    list_display = ('id', 'event_name', 'detachment_report',
                    'is_verified', 'prize_place')


@admin.register(Q12Report)
class Q12ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')


@admin.register(Q12Ranking)
class Q12RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q12TandemRanking)
class Q12TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


class Q13EventOrganizationInline(admin.TabularInline):
    model = Q13EventOrganization
    extra = 0


@admin.register(Q13DetachmentReport)
class Q13DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
    )
    inlines = [Q13EventOrganizationInline]
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'


@admin.register(Q13Ranking)
class Q13RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q13TandemRanking)
class Q13TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q14DetachmentReport)
class Q14DetachmentReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'is_verified')


@admin.register(Q14Ranking)
class Q14RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q14TandemRanking)
class Q14TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q15Rank)
class Q15RankingAdmin(QBaseRankingAdmin):
    pass


class Q15GrantWinnerInline(admin.TabularInline):
    model = Q15GrantWinner
    extra = 0


@admin.register(Q15DetachmentReport)
class Q15DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
        'score',
    )
    inlines = [Q15GrantWinnerInline]
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'



@admin.register(Q15TandemRank)
class Q15TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q16Report)
class Q16ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'is_verified', 'score')


@admin.register(Q16Ranking)
class Q16RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q16TandemRanking)
class Q16TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q17Ranking)
class Q17RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q17TandemRanking)
class Q17TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q17DetachmentReport)
class Q17DetachmentReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'is_verified')


@admin.register(Q18Ranking)
class Q18RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q18DetachmentReport)
class Q18DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
        'is_verified',
        'score',
        'participants_number',
        'june_15_detachment_members',
    )
    list_filter = ('is_verified',)
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'



@admin.register(Q18TandemRanking)
class Q18TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q19Report)
class Q19ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'is_verified', 'safety_violations')


@admin.register(Q19Ranking)
class Q19RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q19TandemRanking)
class Q19TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q20Report)
class Q20ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'is_verified', 'score')


@admin.register(Q20Ranking)
class Q20RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q20TandemRanking)
class Q20TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass
