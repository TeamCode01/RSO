from django.contrib import admin

from competitions.forms import (CompetitionApplicationsForm,
                                CompetitionParticipantsForm)
from competitions.models import (Q7, Q8, Q9, Q10, Q11, Q12,
                                 CompetitionApplications,
                                 CompetitionParticipants, Competitions,
                                 LinksQ7, LinksQ8, OverallRanking,
                                 OverallTandemRanking, Q1Ranking, Q1Report,
                                 Q1TandemRanking, Q2DetachmentReport,
                                 Q2Ranking, Q2TandemRanking, Q3Ranking,
                                 Q3TandemRanking, Q4Ranking, Q4TandemRanking,
                                 Q5DetachmentReport, Q5EducatedParticipant,
                                 Q5Ranking, Q5TandemRanking,
                                 Q6DetachmentReport, Q6Ranking,
                                 Q6TandemRanking, Q7Ranking, Q7Report,
                                 Q7TandemRanking, Q8Ranking, Q8Report,
                                 Q8TandemRanking, Q9Ranking, Q9Report,
                                 Q9TandemRanking, Q10Ranking, Q10Report,
                                 Q10TandemRanking, Q11Ranking, Q11Report,
                                 Q11TandemRanking, Q12Ranking, Q12Report,
                                 Q12TandemRanking, Q13DetachmentReport,
                                 Q13EventOrganization, Q13Ranking,
                                 Q13TandemRanking, Q14DetachmentReport,
                                 Q14LaborProject, Q14Ranking, Q14TandemRanking,
                                 Q15DetachmentReport, Q15GrantWinner, Q15Rank,
                                 Q15TandemRank, Q16Ranking, Q16Report,
                                 Q16TandemRanking, Q17DetachmentReport,
                                 Q17EventLink, Q17Ranking, Q17TandemRanking,
                                 Q18DetachmentReport, Q18Ranking,
                                 Q18TandemRanking, Q19Ranking, Q19Report,
                                 Q19TandemRanking, Q20Ranking, Q20Report,
                                 Q20TandemRanking, QVerificationLog, ProfessionalCompetitionBlock, SpartakiadBlock,
                                 CreativeFestivalBlock, WorkingSemesterOpeningBlock, CommanderCommissionerSchoolBlock,
                                 SafetyWorkWeekBlock, DemonstrationBlock, PatrioticActionBlock, July15Participant)


@admin.register(July15Participant)
class July15ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        'detachment',
        'participants_number',
        'members_number',
    )
    search_fields = ('detachment__name',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Competitions)
class CompetitionsAdmin(admin.ModelAdmin):
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


class QBaseRankingAdmin(admin.ModelAdmin):
    list_display = ('id', 'competition_id', 'detachment', 'place')
    search_fields = ('detachment__name', 'place')

    def has_add_permission(self, request, obj=None):
        return False


class QBaseTandemRankingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'competition_id', 'detachment', 'junior_detachment', 'place'
    )
    search_fields = ('detachment__name', 'junior_detachment__name', 'place')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OverallRanking)
class OverallRankingAdmin(admin.ModelAdmin):
    list_display = ('id', 'competition_id', 'detachment', 'places_sum', 'place')
    search_fields = ('detachment__name', 'place')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OverallTandemRanking)
class OverallTandemRankingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'competition_id', 'detachment', 'junior_detachment', 'places_sum', 'place'
    )
    search_fields = ('detachment__name', 'junior_detachment__name', 'place')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q1Report)
class Q1ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')
    search_fields = ('detachment__name', 'score')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q1Ranking)
class Q1RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q1TandemRanking)
class Q1TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q2DetachmentReport)
class Q2DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
    )
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'


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


@admin.register(DemonstrationBlock)
class DemonstrationBlockAdmin(admin.ModelAdmin):
    list_display = ('report', 'first_may_demonstration', 'first_may_demonstration_participants', 'is_verified')



@admin.register(PatrioticActionBlock)
class PatrioticActionBlockAdmin(admin.ModelAdmin):
    list_display = ('report', 'patriotic_action', 'patriotic_action_participants', 'is_verified')



@admin.register(SafetyWorkWeekBlock)
class SafetyWorkWeekBlockAdmin(admin.ModelAdmin):
    list_display = ('report', 'safety_work_week', 'is_verified')


@admin.register(CommanderCommissionerSchoolBlock)
class CommanderCommissionerSchoolBlockAdmin(admin.ModelAdmin):
    list_display = ('report', 'commander_commissioner_school', 'is_verified')


@admin.register(WorkingSemesterOpeningBlock)
class WorkingSemesterOpeningBlockAdmin(admin.ModelAdmin):
    list_display = ('report', 'working_semester_opening', 'working_semester_opening_participants', 'is_verified')


@admin.register(CreativeFestivalBlock)
class CreativeFestivalBlockAdmin(admin.ModelAdmin):
    list_display = ('report', 'creative_festival', 'is_verified')


@admin.register(ProfessionalCompetitionBlock)
class ProfessionalCompetitionBlockAdmin(admin.ModelAdmin):
    list_display = ('report', 'professional_competition', 'is_verified')


@admin.register(SpartakiadBlock)
class SpartakiadBlockAdmin(admin.ModelAdmin):
    list_display = ('report', 'spartakiad', 'is_verified')


@admin.register(Q6DetachmentReport)
class Q6DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
        'score',
        'get_first_may_demonstration',
        'get_first_may_demonstration_participants',
        'get_first_may_demonstration_verification_status',
        'get_creative_festival',
        'get_creative_festival_verification_status',
        'get_patriotic_action',
        'get_patriotic_action_participants',
        'get_patriotic_action_verification_status',
        'get_safety_work_week',
        'get_safety_work_week_verification_status',
        'get_commander_commissioner_school',
        'get_commander_commissioner_school_verification_status',
        'get_working_semester_opening',
        'get_working_semester_opening_participants',
        'get_working_semester_opening_verification_status',
        'get_spartakiad',
        'get_spartakiad_verification_status',
        'get_professional_competition',
        'get_professional_competition_verification_status',
        'april_1_detachment_members',
    )
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'

    def get_first_may_demonstration(self, obj):
        return obj.demonstration_block.first_may_demonstration
    get_first_may_demonstration.short_description = 'Первомайская демонстрация'
    get_first_may_demonstration.admin_order_field = 'demonstration_block__first_may_demonstration'

    def get_first_may_demonstration_participants(self, obj):
        return obj.demonstration_block.first_may_demonstration_participants
    get_first_may_demonstration_participants.short_description = 'Участники Первомайской демонстрации'
    get_first_may_demonstration_participants.admin_order_field = 'demonstration_block__first_may_demonstration_participants'

    def get_first_may_demonstration_verification_status(self, obj):
        return obj.demonstration_block.is_verified
    get_first_may_demonstration_verification_status.short_description = 'Верификация Первомайской демонстрации'
    get_first_may_demonstration_verification_status.boolean = True

    def get_creative_festival(self, obj):
        return obj.creative_festival_block.creative_festival
    get_creative_festival.short_description = 'Творческий фестиваль'
    get_creative_festival.admin_order_field = 'creative_festival_block__creative_festival'

    def get_creative_festival_verification_status(self, obj):
        return obj.creative_festival_block.is_verified
    get_creative_festival_verification_status.short_description = 'Верификация Творческого фестиваля'
    get_creative_festival_verification_status.boolean = True

    def get_patriotic_action(self, obj):
        return obj.patriotic_action_block.patriotic_action
    get_patriotic_action.short_description = 'Патриотическая акция'
    get_patriotic_action.admin_order_field = 'patriotic_action_block__patriotic_action'

    def get_patriotic_action_participants(self, obj):
        return obj.patriotic_action_block.patriotic_action_participants
    get_patriotic_action_participants.short_description = 'Участники патриотической акции'
    get_patriotic_action_participants.admin_order_field = 'patriotic_action_block__patriotic_action_participants'

    def get_patriotic_action_verification_status(self, obj):
        return obj.patriotic_action_block.is_verified
    get_patriotic_action_verification_status.short_description = 'Верификация Патриотической акции'
    get_patriotic_action_verification_status.boolean = True

    def get_safety_work_week(self, obj):
        return obj.safety_work_week_block.safety_work_week
    get_safety_work_week.short_description = 'Неделя охраны труда'
    get_safety_work_week.admin_order_field = 'safety_work_week_block__safety_work_week'

    def get_safety_work_week_verification_status(self, obj):
        return obj.safety_work_week_block.is_verified
    get_safety_work_week_verification_status.short_description = 'Верификация Недели охраны труда'
    get_safety_work_week_verification_status.boolean = True

    def get_commander_commissioner_school(self, obj):
        return obj.commander_commissioner_school_block.commander_commissioner_school
    get_commander_commissioner_school.short_description = 'Школа подготовки командиров и комиссаров'
    get_commander_commissioner_school.admin_order_field = 'commander_commissioner_school_block__commander_commissioner_school'

    def get_commander_commissioner_school_verification_status(self, obj):
        return obj.commander_commissioner_school_block.is_verified
    get_commander_commissioner_school_verification_status.short_description = 'Верификация Школы подготовки командиров и комиссаров'
    get_commander_commissioner_school_verification_status.boolean = True

    def get_working_semester_opening(self, obj):
        return obj.working_semester_opening_block.working_semester_opening
    get_working_semester_opening.short_description = 'Открытие трудового семестра'
    get_working_semester_opening.admin_order_field = 'working_semester_opening_block__working_semester_opening'

    def get_working_semester_opening_participants(self, obj):
        return obj.working_semester_opening_block.working_semester_opening_participants
    get_working_semester_opening_participants.short_description = 'Участники открытия трудового семестра'
    get_working_semester_opening_participants.admin_order_field = 'working_semester_opening_block__working_semester_opening_participants'

    def get_working_semester_opening_verification_status(self, obj):
        return obj.working_semester_opening_block.is_verified
    get_working_semester_opening_verification_status.short_description = 'Верификация Открытия трудового семестра'
    get_working_semester_opening_verification_status.boolean = True

    def get_spartakiad(self, obj):
        return obj.spartakiad_block.spartakiad
    get_spartakiad.short_description = 'Спартакиада'
    get_spartakiad.admin_order_field = 'spartakiad_block__spartakiad'

    def get_spartakiad_verification_status(self, obj):
        return obj.spartakiad_block.is_verified
    get_spartakiad_verification_status.short_description = 'Верификация Спартакиады'
    get_spartakiad_verification_status.boolean = True

    def get_professional_competition(self, obj):
        return obj.professional_competition_block.professional_competition
    get_professional_competition.short_description = 'Конкурс профессионального мастерства'
    get_professional_competition.admin_order_field = 'professional_competition_block__professional_competition'

    def get_professional_competition_verification_status(self, obj):
        return obj.professional_competition_block.is_verified
    get_professional_competition_verification_status.short_description = 'Верификация Конкурса профессионального мастерства'
    get_professional_competition_verification_status.boolean = True


@admin.register(Q6Ranking)
class Q6RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q6TandemRanking)
class Q6TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


class Q7LinksInline(admin.TabularInline):
    model = LinksQ7
    extra = 0


@admin.register(Q7)
class Q7Admin(admin.ModelAdmin):
    list_display = (
        'id', 'event_name', 'detachment_report', 'is_verified',
        'number_of_participants', 'links'
    )

    inlines = [Q7LinksInline]

    @admin.display(description='Ссылки')
    def links(self, obj):
        return LinksQ7.objects.filter(event=obj).count()

    def has_add_permission(self, request, obj=None):
        return False


class Q7Inline(admin.TabularInline):
    model = Q7
    extra = 0


@admin.register(Q7Report)
class Q7ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')
    search_fields = ('detachment__name',)

    inlines = [Q7Inline]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q7Ranking)
class Q7RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q7TandemRanking)
class Q7TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


class Q8LinksInline(admin.TabularInline):
    model = LinksQ8
    extra = 0

@admin.register(Q8)
class Q8Admin(admin.ModelAdmin):
    list_display = (
        'id', 'event_name', 'detachment_report', 'is_verified',
        'number_of_participants', 'links'
    )

    inlines = [Q8LinksInline]

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Ссылки')
    def links(self, obj):
        return LinksQ8.objects.filter(event=obj).count()


class Q8Inline(admin.TabularInline):
    model = Q8
    extra = 0


@admin.register(Q8Report)
class Q8ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')
    search_fields = ('detachment__name',)

    inlines = [Q8Inline]

    def has_add_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request, obj=None):
        return False


class Q9Inline(admin.TabularInline):
    model = Q9
    extra = 0


@admin.register(Q9Report)
class Q9ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')
    search_fields = ('detachment__name',)

    inlines = [Q9Inline]

    def has_add_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request, obj=None):
        return False


class Q10Inline(admin.TabularInline):
    model = Q10
    extra = 0


@admin.register(Q10Report)
class Q10ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')
    search_fields = ('detachment__name',)

    inlines = [Q10Inline]

    def has_add_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request, obj=None):
        return False



class Q11Inline(admin.TabularInline):
    model = Q11
    extra = 0


@admin.register(Q11Report)
class Q11ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')
    search_fields = ('detachment__name',)

    inlines = [Q11Inline]

    def has_add_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request, obj=None):
        return False


class Q12Inline(admin.TabularInline):
    model = Q12
    extra = 0


@admin.register(Q12Report)
class Q12ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'score')
    search_fields = ('detachment__name',)

    inlines = [Q12Inline]

    def has_add_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q13Ranking)
class Q13RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q13TandemRanking)
class Q13TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


class Q14LaborProjectInline(admin.TabularInline):
    model = Q14LaborProject
    extra = 0

@admin.register(Q14DetachmentReport)
class Q14DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
    )
    inlines = [Q14LaborProjectInline]
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'

    def has_add_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q15TandemRank)
class Q15TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q16Report)
class Q16ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'is_verified', 'score')
    search_fields = ('detachment__name',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q16Ranking)
class Q16RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q16TandemRanking)
class Q16TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


class Q17EventLinkInline(admin.TabularInline):
    model = Q17EventLink
    extra = 0


@admin.register(Q17Ranking)
class Q17RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q17TandemRanking)
class Q17TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q17DetachmentReport)
class Q17DetachmentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competition_id',
        'detachment_id',
        'get_detachment_name',
    )
    inlines = [Q17EventLinkInline]
    search_fields = ('detachment__name',)

    def get_detachment_name(self, obj):
        return obj.detachment.name
    get_detachment_name.admin_order_field = 'detachment__name'
    get_detachment_name.short_description = 'Название отряда'

    def has_add_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q18TandemRanking)
class Q18TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q19Report)
class Q19ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'is_verified', 'safety_violations')
    search_fields = ('detachment__name',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q19Ranking)
class Q19RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q19TandemRanking)
class Q19TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(Q20Report)
class Q20ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'detachment', 'is_verified', 'score')
    search_fields = ('detachment__name',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Q20Ranking)
class Q20RankingAdmin(QBaseRankingAdmin):
    pass


@admin.register(Q20TandemRanking)
class Q20TandemRankingAdmin(QBaseTandemRankingAdmin):
    pass


@admin.register(QVerificationLog)
class QVerificationLogAdmin(admin.ModelAdmin):
    """Таблица логов верификации пользователей."""

    list_display = (
        'competition',
        'verifier',
        'q_number',
        'verified_detachment',
        'action',
        'timestamp'
    )
    readonly_fields = (
        'competition',
        'verifier',
        'q_number',
        'verified_detachment',
        'action',
        'timestamp'
    )
    list_filter = ('timestamp', 'action', 'q_number',)

    def has_add_permission(self, request, obj=None):
        """Запрещаем добавление записи через админку."""
        return False
