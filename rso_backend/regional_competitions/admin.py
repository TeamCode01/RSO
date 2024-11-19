from django.contrib import admin

from regional_competitions.factories import RAdminFactory
from regional_competitions.forms import ExpertUserForm
from regional_competitions.models import (AdditionalStatistic, CHqRejectingLog, ExpertRole, Ranking, RegionalR1, RegionalR15,
                                          RegionalR18,
                                          RegionalR18Link, RegionalR18Project, RegionalR2,
                                          RegionalR4, RegionalR4Event,
                                          RegionalR4Link, RegionalR5,
                                          RegionalR5Event, RegionalR5Link,
                                          RegionalR11, RegionalR12,
                                          RegionalR13, RegionalR14,
                                          RegionalR16, RegionalR16Link,
                                          RegionalR16Project, RegionalR17,
                                          RegionalR19, RegionalR101,
                                          RegionalR101Link, RegionalR102,
                                          RegionalR102Link, RVerificationLog, RegionalR8,
                                          StatisticalRegionalReport,
                                          r6_models_factory, r9_models_factory, RegionalR3,
                                          DumpStatisticalRegionalReport)
from regional_competitions.r_calculations import calculate_r11_score, calculate_r13_score, calculate_r14, calculate_r2_score, calculate_r3_score, update_all_ranking_places
from regional_competitions.tasks import calc_places_r1, calc_places_r10, calc_places_r11, calc_places_r12, calc_places_r13, calc_places_r14, calc_places_r16, calc_places_r2, calc_places_r3, calc_places_r4, calc_places_r5, calc_places_r6, calc_places_r9


class AdditionalStatisticInline(admin.StackedInline):
    model = AdditionalStatistic
    extra = 0


@admin.register(StatisticalRegionalReport)
class StatisticalRegionalReportAdmin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'participants_number',
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
    search_fields = (
        'regional_headquarter__name',
        'regional_headquarter__id',
    )
    inlines = [AdditionalStatisticInline]


@admin.register(DumpStatisticalRegionalReport)
class DumpStatisticalRegionalReportAdmin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'participants_number',
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
    search_fields = (
        'regional_headquarter__name',
        'regional_headquarter__id',
    )


@admin.register(RVerificationLog)
class RVerificationLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'district_headquarter',
        'central_headquarter',
        'regional_headquarter',
        'is_regional_data',
        'is_district_data',
        'is_central_data',
        'report_number',
        'report_id',
        'created_at'
    )
    search_fields = (
        'user__last_name',
        'user__username',
        'district_headquarter__name',
        'central_headquarter__name',
        'regional_headquarter__name',
    )
    list_filter = (
        'district_headquarter',
        'central_headquarter',
        'report_number',
        'is_regional_data',
        'is_district_data',
        'is_central_data',
    )
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': (
                'user',
                'central_headquarter',
                'district_headquarter',
                'regional_headquarter',
                'is_regional_data',
                'is_district_data',
                'is_central_data',
                'report_number',
                'report_id',
                'data'
            )
        }),
        ('Время', {
            'fields': ('created_at',),
        }),
    )


@admin.register(CHqRejectingLog)
class CHqRejectingLogAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'report_number',
        'report_id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'created_at'
    )
    search_fields = (
        'user__username',
        'user__last_name',
        'report_number',
        'report_id'
    )
    list_filter = (
        'report_number',
        'created_at',
        'regional_headquarter',
    )
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': (
                'user',
                'report_number',
                'report_id',
                'reasons'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',),
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('user')
        return queryset

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id if obj.regional_headquarter else '-'
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR1)
class RegionalR1Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'is_sent',
        'score',
        'amount_of_money',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    list_filter = ('verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR2)
class RegionalR2Admin(admin.ModelAdmin):

    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'score',
        'created_at',
        'updated_at'
    )
    search_fields = ('regional_headquarter__name',)
    readonly_fields = ('created_at', 'updated_at')

    actions = ['get_ro_score',]

    def get_ro_score(self, request, queryset):
        for obj in queryset:
            calculate_r2_score(obj)

    get_ro_score.short_description = 'Вычислить очки по показателю'

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR3)
class RegionalR3Admin(admin.ModelAdmin):

    list_display = (
        'regional_headquarter',
        'id',
        'amount_of_membership_fees_2023',
        'score',
    )
    search_fields = ('regional_headquarter__name',)
    actions = ['get_ro_score',]

    def get_ro_score(self, request, queryset):
        for obj in queryset:
            calculate_r3_score(obj)

    get_ro_score.short_description = 'Вычислить очки по показателю'


class RegionalR4LinkInline(admin.TabularInline):
    model = RegionalR4Link
    extra = 0


class RegionalR4EventAdminInline(admin.StackedInline):
    model = RegionalR4Event
    extra = 0

    class RegionalR4LinkInline(admin.TabularInline):
        model = RegionalR4Link
        extra = 0

    inlines = [RegionalR4LinkInline]


@admin.register(RegionalR4Event)
class RegionalR4EventAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_r4',
        'participants_number',
        'start_date',
        'end_date',
        'is_interregional'
    )
    search_fields = ('regional_r4__id',)
    list_filter = ('is_interregional', 'start_date', 'end_date', 'regional_r4')
    inlines = [RegionalR4LinkInline]


@admin.register(RegionalR4)
class RegionalR4Admin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'get_id_regional_headquarter',
        'id',
        'is_sent',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at',
        'score',
    )
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('regional_headquarter__name', 'comment')
    list_filter = ('is_sent', 'verified_by_chq', 'verified_by_dhq')
    inlines = [RegionalR4EventAdminInline]

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


class RegionalR5LinkInline(admin.TabularInline):
    model = RegionalR5Link
    extra = 0


class RegionalR5EventAdminInline(admin.StackedInline):
    model = RegionalR5Event
    extra = 0

    class RegionalR5LinkInline(admin.TabularInline):
        model = RegionalR5Link
        extra = 0

    inlines = [RegionalR5LinkInline]


@admin.register(RegionalR5Event)
class RegionalR5EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'regional_r5', 'participants_number', 'ro_participants_number', 'start_date', 'end_date',)
    search_fields = ('regional_r5__id',)
    list_filter = ('start_date', 'end_date', 'regional_r5')
    inlines = [RegionalR5LinkInline]


@admin.register(RegionalR5)
class RegionalR5Admin(admin.ModelAdmin):
    list_display = (
        'get_id_regional_headquarter',
        'regional_headquarter',
        'id',
        'is_sent',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at',
        'score',
    )
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('regional_headquarter__name', 'comment')
    list_filter = ('is_sent', 'verified_by_chq', 'verified_by_dhq')
    inlines = [RegionalR5EventAdminInline]

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


r6_list_display = (
    'regional_headquarter',
    'id',
    'is_project',
    'is_sent',
    'number_of_members',
    'verified_by_chq',
    'verified_by_dhq',
    'score',
    'created_at',
    'updated_at'
)

r6_list_filter = (
    'is_sent',
    'verified_by_chq',
    'verified_by_dhq'
)

r6_search_fields = ('comment', 'regional_headquarter__name')

r6_readonly_fields = ('created_at', 'updated_at')

r6_admin_factory = RAdminFactory(
    models=r6_models_factory.models,
    list_display=r6_list_display,
    list_filter=r6_list_filter,
    search_fields=r6_search_fields,
    readonly_fields=r6_readonly_fields
)
r6_admin_factory.create_admin_classes()


# r7_list_display = (
#     'regional_headquarter',
#     'id',
#     'prize_place',
#     'document',
#     'verified_by_chq',
#     'verified_by_dhq',
#     'score',
#     'created_at',
#     'updated_at'
# )
#
# r7_list_filter = (
#     'prize_place',
#     'verified_by_chq',
#     'verified_by_dhq'
# )
#
# r7_search_fields = ('comment', 'regional_headquarter__name')
#
# r7_readonly_fields = ('created_at', 'updated_at')
#
# r7_admin_factory = RAdminFactory(
#     models=r7_models_factory.models,
#     list_display=r7_list_display,
#     list_filter=r7_list_filter,
#     search_fields=r7_search_fields,
#     readonly_fields=r7_readonly_fields
# )
# r7_admin_factory.create_admin_classes()


@admin.register(RegionalR8)
class RegionalR8Admin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'score',
        'created_at',
        'updated_at'
    )
    search_fields = ('regional_headquarter__name',)
    readonly_fields = ('regional_headquarter',)


r9_list_display = (
    'regional_headquarter',
    'is_sent',
    'id',
    'event_happened',
    'document',
    'verified_by_chq',
    'verified_by_dhq',
    'score',
    'created_at',
    'updated_at'
)
r9_list_filter = ('is_sent', 'event_happened', 'verified_by_chq', 'verified_by_dhq')
r9_search_fields = ('comment',)
r9_readonly_fields = ('created_at', 'updated_at')

r9_admin_factory = RAdminFactory(
    models=r9_models_factory.models,
    list_display=r9_list_display,
    list_filter=r9_list_filter,
    search_fields=r9_search_fields,
    readonly_fields=r9_readonly_fields
)
r9_admin_factory.create_admin_classes()


class RegionalR101LinkInline(admin.TabularInline):
    model = RegionalR101Link
    extra = 0


@admin.register(RegionalR101)
class RegionalR101Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_id_regional_headquarter',
        'regional_headquarter',
        'is_sent',
        'event_happened',
        'document',
        'verified_by_chq',
        'verified_by_dhq',
        'score',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment',)
    list_filter = ('is_sent', 'event_happened', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RegionalR101LinkInline]

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


class RegionalR102LinkInline(admin.TabularInline):
    model = RegionalR102Link
    extra = 0


@admin.register(RegionalR102)
class RegionalR102Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_id_regional_headquarter',
        'regional_headquarter',
        'is_sent',
        'event_happened',
        'document',
        'verified_by_chq',
        'verified_by_dhq',
        'score',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment',)
    list_filter = ('is_sent', 'event_happened', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RegionalR102LinkInline]

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR11)
class RegionalR11Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'is_sent',
        'score',
        'participants_number',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    list_filter = ('is_sent', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR12)
class RegionalR12Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'is_sent',
        'score',
        'amount_of_money',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    list_filter = ('is_sent', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR13)
class RegionalR13Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'is_sent',
        'score',
        'number_of_members',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    list_filter = ('is_sent', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['get_ro_score',]

    @admin.action(description='Вычислить очки по показателю')
    def get_ro_score(self, request, queryset):
        calculate_r13_score()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('regional_headquarter')

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR14)
class RegionalR14Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'report_12',
        'report_13',
        'score'
    )
    search_fields = ('id', 'report_12__regional_headquarter__name')

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR15)
class RegionalR15Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'xp',
        'yp',
        'x3',
        'y3',
        'p15'
    )
    search_fields = ('id', 'regional_headquarter__name')

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


class RegionalR16LinkInline(admin.TabularInline):
    model = RegionalR16Link
    extra = 0


class RegionalR16ProjectInline(admin.TabularInline):
    model = RegionalR16Project
    extra = 0


@admin.register(RegionalR16Project)
class RegionalR16ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_r16',
        'name',
        'project_scale',
        'regulations'
    )
    search_fields = ('name',)
    list_filter = ('project_scale',)
    inlines = [RegionalR16LinkInline]


@admin.register(RegionalR16)
class RegionalR16Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_id_regional_headquarter',
        'regional_headquarter',
        'is_sent',
        'is_project',
        'score',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment',)
    list_filter = ('is_sent', 'is_project', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RegionalR16ProjectInline]

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR17)
class RegionalR17Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    readonly_fields = ('created_at', 'updated_at')

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


class RegionalR18LinkInline(admin.TabularInline):
    model = RegionalR18Link
    extra = 0


class RegionalR18ProjectInline(admin.TabularInline):
    model = RegionalR18Project
    extra = 0


@admin.register(RegionalR18Project)
class RegionalR18ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_r18',
        'file',
    )
    search_fields = ('name',)
    inlines = [RegionalR18LinkInline]


@admin.register(RegionalR18)
class RegionalR18Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RegionalR18ProjectInline]

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(RegionalR19)
class RegionalR19Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'get_id_regional_headquarter',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    readonly_fields = ('created_at', 'updated_at')

    def get_id_regional_headquarter(self, obj):
        return obj.regional_headquarter.id
    get_id_regional_headquarter.short_description = 'ID РШ'


@admin.register(ExpertRole)
class ExpertRoleAdmin(admin.ModelAdmin):
    form = ExpertUserForm
    list_display = (
        'id',
        'user',
        'central_headquarter',
        'district_headquarter',
        'created_at',
    )
    search_fields = (
        'user__username',
        'central_headquarter__name',
        'district_headquarter__name'
    )


@admin.register(Ranking)
class RankingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'overall_place',
        'k_place',
        'sum_overall_place',
        'sum_k_place',
        'r1_place',
        'r2_place',
        'r3_place',
        'r4_place',
        'r5_place',
        'r6_place',
        'r7_place',
        'r8_place',
        'r9_place',
        'r10_place',
        'r11_place',
        'r12_place',
        'r13_place',
        'r14_place',
        'r15_place',
        'r16_place',
    )
    search_fields = (
        'regional_headquarter__name',
    )
    list_filter = ('regional_headquarter',)

    actions = [
        'get_r1_places',
        'get_r2_places',
        'get_r3_places',
        'get_r4_places',
        'get_r5_places',
        'get_r6_places',
        'get_r9_places',
        'get_r10_places',
        'get_r11_places',
        'get_r12_places',
        'get_r13_places',
        'get_r14_places',
        'get_r16_places',
        'get_overall_places',
        'calculate_all_places',
    ]

    @admin.action(description='Вычислить места по 1 показателю')
    def get_r1_places(self, request, queryset):
        calc_places_r1()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 2 показателю')
    def get_r2_places(self, request, queryset):
        calc_places_r2()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 3 показателю')
    def get_r3_places(self, request, queryset):
        calc_places_r3()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 4 показателю')
    def get_r4_places(self, request, queryset):
        calc_places_r4()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 5 показателю')
    def get_r5_places(self, request, queryset):
        calc_places_r5()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 6 показателю')
    def get_r6_places(self, request, queryset):
        calc_places_r6()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 9 показателю')
    def get_r9_places(self, request, queryset):
        calc_places_r9()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 10 показателю')
    def get_r10_places(self, request, queryset):
        calc_places_r10()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 11 показателю')
    def get_r11_places(self, request, queryset):
        calculate_r11_score()
        calc_places_r11()

    @admin.action(description='Вычислить места по 12 показателю')
    def get_r12_places(self, request, queryset):
        calc_places_r12()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 13 показателю')
    def get_r13_places(self, request, queryset):
        calculate_r13_score()
        calc_places_r13()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 14 показателю')
    def get_r14_places(self, request, queryset):
        calculate_r14()
        calc_places_r14()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить места по 16 показателю')
    def get_r16_places(self, request, queryset):
        calc_places_r16()
        self.message_user(request, 'Расчитано.')

    @admin.action(description='Вычислить итоговые места')
    def get_overall_places(self, request, queryset):
        update_all_ranking_places()
        self.message_user(request, 'Расчитано.')


    @admin.action(description='Вычислить места по всем показателям + итоговые')
    def calculate_all_places(self, request, queryset):
        """
        Вычисляет места по всем показателям и обновляет итоговые места.
        """
        self.get_r1_places(request, queryset)
        self.get_r2_places(request, queryset)
        self.get_r3_places(request, queryset)
        self.get_r4_places(request, queryset)
        self.get_r5_places(request, queryset)
        self.get_r6_places(request, queryset)
        self.get_r9_places(request, queryset)
        self.get_r10_places(request, queryset)
        self.get_r11_places(request, queryset)
        self.get_r12_places(request, queryset)
        self.get_r13_places(request, queryset)
        self.get_r14_places(request, queryset)
        self.get_r16_places(request, queryset)

        self.get_overall_places(request, queryset)

        self.message_user(request, 'Все показатели и итоговые места успешно рассчитаны.')
